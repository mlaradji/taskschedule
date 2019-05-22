"""Command line interface of taskschedule"""

import time
import curses
import argparse

from taskschedule.schedule import Schedule


def draw(stdscr, refresh_rate=1, hide_empty=True, scheduled='today', completed=True):
    """Draw the schedule using curses."""
    schedule = Schedule()
    curses.curs_set(0)
    curses.start_color()
    curses.init_pair(1, 20, curses.COLOR_BLACK)
    curses.init_pair(2, 8, 0)  # Hours
    curses.init_pair(3, 20, 234)  # Alternating background
    curses.init_pair(4, curses.COLOR_WHITE, curses.COLOR_BLACK)  # Header
    curses.init_pair(5, curses.COLOR_GREEN, curses.COLOR_BLACK)  # Current hour
    curses.init_pair(6, 19, 234)  # Completed task - alternating background
    curses.init_pair(7, 19, 0)  # Completed task

    while True:
        max_y, max_x = stdscr.getmaxyx()

        stdscr.clear()

        schedule.get_tasks(scheduled=scheduled, completed=completed)
        rows = schedule.format_as_table(hide_empty=hide_empty).splitlines()
        header = rows[0]
        data = rows[1:]

        # Draw header
        for i, char in enumerate(header):
            if char == ' ':
                color = curses.color_pair(1)
            else:
                color = curses.color_pair(4) | curses.A_UNDERLINE
            stdscr.addstr(0, i, char, color)

        # Draw schedule
        for i, row in enumerate(data):
            # Draw hours
            current_hour = time.localtime().tm_hour
            if int(row[:2]) == current_hour:
                stdscr.addstr(i+1, 0, row[:2], curses.color_pair(5))
            else:
                stdscr.addstr(i+1, 0, row[:2], curses.color_pair(2))

            # Get task details
            details = row[2:]
            if len(details) > max_x:  # Too long: truncate
                details = details[0:max_x - 5] + '...'
            else:  # Fill remaining width with spaces
                details = details + ' ' * (max_x - len(details) - 2)

            # Draw using alternating background
            if i % 2:
                if details[6] == "0":
                    color = curses.color_pair(7)
                else:
                    color = curses.color_pair(1)
            else:
                if details[6] == "0":
                    color = curses.color_pair(6)
                else:
                    color = curses.color_pair(3)


            stdscr.addstr(i+1, 2, details, color)

        stdscr.refresh()
        time.sleep(refresh_rate)


def main(argv):
    """Display a schedule report for taskwarrior."""
    parser = argparse.ArgumentParser(
        description="""Display a schedule report for taskwarrior."""
    )
    parser.add_argument(
        '-r', '--refresh', help="refresh every n seconds", type=int, default=1
    )
    parser.add_argument(
        '-s', '--scheduled', help="scheduled date: ex. 'today', 'tomorrow'",
        type=str, default='today'
    )
    parser.add_argument(
        '-a', '--all', help="show all hours, even if empty",
        action='store_true', default=False
    )
    parser.add_argument(
        '-c', '--completed', help="hide completed tasks",
        action='store_false', default=True
    )
    args = parser.parse_args(argv)

    hide_empty = not args.all
    curses.wrapper(draw, args.refresh, hide_empty, args.scheduled, args.completed)
