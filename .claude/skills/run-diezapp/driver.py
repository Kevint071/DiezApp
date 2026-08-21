"""Drive the running DiezApp Flet web build with Playwright + system Chrome.

DiezApp renders through Flutter's CanvasKit (a <canvas>, no DOM text nodes and
no accessibility tree until a screen reader is toggled on), so this driver
uses screenshot-then-click-by-coordinate rather than text/ARIA locators.

Usage (app must already be running via `flet run -w`, see SKILL.md):

    python driver.py <url> <command> [command ...]

Commands (space-separated tokens per command, semicolon-separated commands):
    shot:<path>              take a screenshot, save to <path>
    click:<x>,<y>             mouse click at viewport coordinates
    type:<text>               type text at current focus (use _ for spaces)
    wait:<ms>                 pause for <ms> milliseconds
    key:<name>                press a keyboard key (e.g. Enter, Backspace)

Example:
    python driver.py http://127.0.0.1:8551/ \
        "shot:out/home.png" \
        "click:200,120" "wait:800" \
        "click:200,89" "type:1000" \
        "click:210,148" "wait:1200" \
        "shot:out/result.png"
"""

import sys

from playwright.sync_api import sync_playwright

VIEWPORT = {"width": 420, "height": 900}


def run(url: str, commands: list[str]) -> None:
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="chrome", headless=True)
        page = browser.new_page(viewport=VIEWPORT)
        page.goto(url, wait_until="networkidle", timeout=30000)
        page.wait_for_timeout(1500)

        for cmd in commands:
            kind, _, arg = cmd.partition(":")
            if kind == "shot":
                page.screenshot(path=arg)
                print(f"[shot] saved {arg}")
            elif kind == "click":
                x_str, y_str = arg.split(",")
                page.mouse.click(float(x_str), float(y_str))
                print(f"[click] {arg}")
            elif kind == "type":
                page.keyboard.type(arg.replace("_", " "))
                print(f"[type] {arg}")
            elif kind == "wait":
                page.wait_for_timeout(int(arg))
            elif kind == "key":
                page.keyboard.press(arg)
                print(f"[key] {arg}")
            else:
                raise ValueError(f"unknown command: {cmd}")

        browser.close()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    run(sys.argv[1], sys.argv[2:])
