# -*- encoding: utf-8 -*-
"""
https://github.com/lxnt/df-structures
Copyright (c) 2012-2012 Alexander Sabourenkov (screwdriver@lxnt.info)
Copyright (c) 2009-2011 Petr Mrázek (peterix@gmail.com)

This software is provided 'as-is', without any express or implied
warranty. In no event will the authors be held liable for any
damages arising from the use of this software.

Permission is granted to anyone to use this software for any
purpose, including commercial applications, and to alter it and
redistribute it freely, subject to the following restrictions:

1. The origin of this software must not be misrepresented; you must
not claim that you wrote the original software. If you use this
software in a product, an acknowledgment in the product documentation
would be appreciated but is not required.

2. Altered source versions must be plainly marked as such, and
must not be misrepresented as being the original software.

3. This notice may not be removed or altered from any source
distribution.
"""

from textwrap import dedent
dependencies = {
    "coord": set(["coord2d"]),
    }
methods = {
    "coord2d": dedent("""
                coord2d():  x(-30000), y(-30000) {};
                coord2d(uint16_t _x, uint16_t _y) : x(_x), y(_y) {};
                bool valid() const { return x != -30000; }
                bool in(const coord2d &e) const {
                    return x >= 0 and x < e.x and y >= 0 and y < e.y;
                }
                void clear() { x = y = -30000; }
                bool operator==(const coord2d &other) const {
                    return (x == other.x) && (y == other.y);
                }
                bool operator!=(const coord2d &other) const {
                    return (x != other.x) || (y != other.y);
                }
                bool operator<(const coord2d &other) const {
                    if (x != other.x) return (x < other.x);
                    return y < other.y;
                }
                coord2d operator+(const coord2d &other) const {
                    return coord2d(x + other.x, y + other.y);
                }
                coord2d operator-(const coord2d &other) const {
                    return coord2d(x - other.x, y - other.y);
                }
                coord2d operator/(int number) const {
                    return coord2d(x/number, y/number);
                }
                coord2d operator*(int number) const {
                    return coord2d(x*number, y*number);
                }
                coord2d operator%(int number) const {
                    return coord2d(x%number, y%number);
                }    """).splitlines(),
    "coord": dedent("""
                coord():  x(-30000), y(-30000), z(-30000) {};
                coord(const coord2d &c, uint16_t _z) : x(c.x), y(c.y), z(_z) {};
                coord(uint16_t _x, uint16_t _y, uint16_t _z) : x(_x), y(_y), z(_z) {};
                operator coord2d() const { return coord2d(x,y); }
                bool valid() const { return x != -30000; }
                void clear() { x = y = z = -30000; }
                bool in(const coord &e) const {
                    return x >= 0 and x < e.x and y >= 0 and y < e.y and z >= 0 and z < e.z;
                }                
                bool operator<(const coord &other) const {
                    if (x != other.x) return (x < other.x);
                    if (y != other.y) return (y < other.y);
                    return z < other.z;
                }
                bool operator==(const coord &other) const {
                    return (x == other.x) && (y == other.y) && (z == other.z);
                }
                bool operator!=(const coord &other) const{
                    return (x != other.x) || (y != other.y) || (z != other.z);
                }
                coord operator+(const coord &other) const {
                    return coord(x + other.x, y + other.y, z + other.z);
                }
                coord operator-(const coord &other) const {
                    return coord(x - other.x, y - other.y, z - other.z);
                }

                coord operator/(int number) const {
                    return coord(x/number, y/number, z);
                }
                coord operator*(int number) const
                {
                    return coord(x*number, y*number, z);
                }
                coord operator%(int number) const {
                    return coord(x%number, y%number, z);
                }
                coord operator-(int number) const {
                    return coord(x,y,z-number);
                }
                coord operator+(int number) const {
                    return coord(x,y,z+number);
                } """).splitlines(),
    }