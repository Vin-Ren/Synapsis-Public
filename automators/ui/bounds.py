
import re

from typing import Tuple


class Bounds:
    BOUNDS_REGEX = r'\[([0-9]*?),([0-9]*?)\]\[([0-9]*?),([0-9]*?)\]'

    @classmethod
    def get(cls, bounds) -> Tuple[Tuple[int,int], Tuple[int,int]]:
        # bounds value = "[x1,y1][x2,y2]"
        #                       x1      y1       x2      y2
        # so regex would be '[([0-9]),([0-9])][([0-9]),([0-9])]'
        # split each value to its individual group, so x1 would be group(1), y1 group(2) and so on.
        regex = re.compile(cls.BOUNDS_REGEX)

        match = regex.match(bounds)
        if match:
            x1,y1, x2,y2 = [val for val in [match.group(i) for i in range(1,5)]] # nested list-comp
            return ((int(x1), int(y1)),
                    (int(x2), int(y2)))
        return ((-1, -1), # Escaping None return value
                (-1,-1))

    @classmethod
    def get_center(cls, boundsCoordinates:Tuple[Tuple[int,int], Tuple[int,int]]):
        (x1, y1), (x2, y2) = boundsCoordinates

        middleX = int(round((x1+x2)/2))
        middleY = int(round((y1+y2)/2))
        return (middleX, middleY)

    @classmethod
    def shift(cls, bounds: Tuple[Tuple[int,int], Tuple[int,int]], shift: int = -1):
        """ Shifts bounds with the given shift, if negative, it will shift to the inside of the bounds.
        :param: bounds: 2D array of the coordinates.
        :param: shift: shift that will be given to the bounds.
        """
        return ((bounds[0][0]-shift, bounds[0][1]-shift),(bounds[1][0]+shift, bounds[1][1]+shift))
