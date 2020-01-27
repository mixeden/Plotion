import io
import os
import string
import random
from os import path
from threading import Thread
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from notion.block import ImageBlock
from notion.client import NotionClient

from NotionGraphsDrawer.settings import TOKEN

PAGES = [
    "https://www.notion.so/mixedself/Dashboard-40a3156030fd4d9cb1935993e1f2c7eb"
]
BASE_KEY = "Base:"
X_AXIS_KEY = "X axis:"
Y_AXIS_KEY = "Y axis:"


def br_text(text):
    return "__" + text + "__"


def clear_text(text):
    return text.replace(br_text(BASE_KEY), "").replace(BASE_KEY, "") \
        .replace(br_text(X_AXIS_KEY), "").replace(X_AXIS_KEY, "") \
        .replace(br_text(Y_AXIS_KEY), "").replace(Y_AXIS_KEY, "").strip()


def get_point_from_row(thing, row):
    x_property = row.get_property(thing["x"])
    y_property = row.get_property(thing["y"])

    if thing["x"] == "date":
        x_property = x_property.start

    if thing["y"] == "date":
        y_property = y_property.start

    return x_property, y_property


def get_lines_array(thing, client):
    database = client.get_collection_view(thing["database"])
    rows = database.default_query().execute()
    lines_array = []

    for i in range(1, len(rows)):
        previous_row = rows[i - 1]
        current_row = rows[i]
        line = [(get_point_from_row(thing, previous_row)), (get_point_from_row(thing, current_row))]
        lines_array.append(line)

    return lines_array


def get_empty_object():
    return {
        "database": "",
        "x": "",
        "y": ""
    }


def is_not_empty(thing):
    return thing != ""


def check_for_completeness(object):
    return is_not_empty(object["database"]) and is_not_empty(object["x"]) and is_not_empty(object["y"])


def random_string(string_length=10):
    letters = string.ascii_lowercase
    return ''.join(random.choice(letters) for i in range(string_length))


def reparse_points(points):
    return [
        [points[0][0], points[1][0]],
        [points[0][1], points[1][1]],
    ]


def x_axis_dates(ax=None, fig=None):
    if ax is None:
        ax = plt.gca()

    if fig is None:
        fig = plt.gcf()

    loc = mdates.AutoDateLocator()
    fmt = mdates.AutoDateFormatter(loc)

    ax.xaxis.set_major_locator(loc)
    ax.xaxis.set_major_formatter(fmt)

    fig.autofmt_xdate()


def draw_plot(client, thing, block, page):
    photo = page.children.add_new(ImageBlock)
    photo.move_to(block, "after")

    array = get_lines_array(thing, client)
    print(array)

    for i in range(1, len(array)):
        points = reparse_points(array[i - 1:i][0])
        plt.plot(points[0], points[1], color="red")

    if not path.exists("images"):
        os.mkdir("images")

    if thing["x"] == "date":
        x_axis_dates()

    filename = "images/" + random_string(15) + ".png"
    plt.savefig(filename)

    print("Uploading " + filename)
    photo.upload_file(filename)


def plot():
    client = NotionClient(token_v2=TOKEN)

    for page in PAGES:
        blocks = client.get_block(page)
        thing = get_empty_object()

        for i in range(len(blocks.children)):
            block = blocks.children[i]
            print(block.type)

            if block.type != "image":
                title = block.title

                if BASE_KEY in title:
                    thing["database"] = clear_text(title).split("](")[0].replace("[", "")

                elif X_AXIS_KEY in title:
                    thing["x"] = clear_text(title)

                elif Y_AXIS_KEY in title:
                    thing["y"] = clear_text(title)

                    if check_for_completeness(thing):
                        # not last block
                        if i != len(blocks.children) - 1:
                            next_block = blocks.children[i + 1]

                            # if next block is picture, then it is previous
                            # version of the plot, then we should remove it
                            if blocks.children[i + 1].type == "image":
                                next_block.remove()

                        draw_plot(client, thing, block, blocks)
                        thing = get_empty_object()


@csrf_exempt
def index(request):
    if request.method == "POST":
        thread = Thread(target=plot)
        thread.start()

        return HttpResponse("Hello, world.")

    else:
        return HttpResponse("Hello, world.")
