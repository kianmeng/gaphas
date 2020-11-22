from functools import singledispatch
from typing import Tuple, Union

from gaphas.aspect.connector import ConnectionSink, Connector
from gaphas.connector import Handle, Port
from gaphas.item import Item
from gaphas.types import Pos
from gaphas.view import GtkView


class ItemHandleMove:
    """Move a handle (role is applied to the handle)"""

    GLUE_DISTANCE = 10

    last_x: float
    last_y: float

    def __init__(self, item: Item, handle: Handle, view: GtkView):
        self.item = item
        self.handle = handle
        self.view = view

    def start_move(self, pos: Pos):
        self.last_x, self.last_y = pos
        canvas = self.view.canvas

        cinfo = canvas.connections.get_connection(self.handle)
        if cinfo:
            canvas.solver.remove_constraint(cinfo.constraint)

    def move(self, pos: Pos):
        item = self.item
        view = self.view

        v2i = view.get_matrix_v2i(item)

        x, y = v2i.transform_point(*pos)

        self.handle.pos = (x, y)

        sink = self.glue(pos)

        # do not request matrix update as matrix recalculation will be
        # performed due to item normalization if required
        view.canvas.request_update(item, matrix=False)

        return sink

    def stop_move(self, pos):
        pass

    def glue(self, pos: Pos, distance=GLUE_DISTANCE):
        """Glue to an item near a specific point.

        Returns a ConnectionSink or None.
        """
        item = self.item
        handle = self.handle
        view = self.view

        if not handle.connectable:
            return None

        connectable, port, glue_pos = port_at_point(
            view, pos, distance=distance, exclude=(item,)
        )

        # check if item and found item can be connected on closest port
        if connectable and port and glue_pos:
            connections = self.view.canvas.connections
            connector = Connector(self.item, self.handle, connections)
            sink = ConnectionSink(connectable, port)

            if connector.allow(sink):
                # transform coordinates from view space to the item
                # space and update position of item's handle
                v2i = view.get_matrix_v2i(item).transform_point
                handle.pos = v2i(*glue_pos)
                return sink
        return None


HandleMove = singledispatch(ItemHandleMove)


def port_at_point(
    view, vpos, distance=10, exclude=None
) -> Union[Tuple[Item, Port, Tuple[float, float]], Tuple[None, None, None]]:
    """Find item with port closest to specified position.

    List of items to be ignored can be specified with `exclude`
    parameter.

    Tuple is returned

    - found item
    - closest, connectable port
    - closest point on found port (in view coordinates)

    :Parameters:
        vpos
        Position specified in view coordinates.
        distance
        Max distance from point to a port (default 10)
        exclude
        Set of items to ignore.
    """
    v2i = view.get_matrix_v2i
    vx, vy = vpos

    max_dist = distance
    port = None
    glue_pos = None
    item = None

    rect = (vx - distance, vy - distance, distance * 2, distance * 2)
    for i in reversed(list(view.get_items_in_rectangle(rect))):
        if i in exclude:
            continue
        for p in i.ports():
            if not p.connectable:
                continue

            ix, iy = v2i(i).transform_point(vx, vy)
            pg, d = p.glue((ix, iy))

            if d >= max_dist:
                continue

            max_dist = d
            item = i
            port = p

            # transform coordinates from connectable item space to view
            # space
            i2v = view.get_matrix_i2v(i).transform_point
            glue_pos = i2v(*pg)
    return item, port, glue_pos  # type: ignore[return-value]
