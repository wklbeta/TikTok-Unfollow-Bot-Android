import xml.etree.ElementTree as ET
import subprocess
import os

node_tag = "node"
followed_btn_class = "android.widget.Button"
uiautomator_file_name = "window_dump.xml"
list_container_class = "androidx.recyclerview.widget.RecyclerView"


def click_by_text(xml_path, text):
    tree = ET.parse(xml_path)
    root = tree.getroot()

    for elem in root.iter(node_tag):
        if text in elem.attrib.get("text", ""):
            text_center = bounds_str_to_center(elem.attrib.get("bounds", ""))
            subprocess.run(
                f"adb shell input tap {text_center[0]} {text_center[1]}".split()
            )
            return True

    return False


def find_node_bounds(xml_path, density_scale, followed_text):
    tree = ET.parse(xml_path)
    root = tree.getroot()

    btn_bounds_center_list = []
    list_container_bounds = []
    for elem in root.iter(node_tag):
        if list_container_class in elem.attrib.get("class", ""):
            list_container_bounds = get_bounds(elem.attrib.get("bounds", ""))
            print("Found list container bounds:", list_container_bounds)
        if len(list_container_bounds) == 0:
            continue
        if elem.attrib["class"] == followed_btn_class and (
            followed_text == "" or elem.attrib["text"] == followed_text
        ):
            bounds = elem.attrib.get("bounds", "")
            left, top, right, bottom = get_bounds(bounds)
            center = [(left + right) // 2, (top + bottom) // 2]
            button_width_in_dp = int((right - left) / density_scale)
            button_height_in_dp = int((bottom - top) / density_scale)
            if followed_text == "":
                followed_text = elem.attrib.get("text", None)
                print("Found followed button text: {}".format(followed_text))
                print(  
                    "Button size in dp: {}x{}".format(
                        button_width_in_dp, button_height_in_dp
                    )
                )
            if 70 <= button_width_in_dp <= 140 and 24 <= button_height_in_dp <= 40:
                btn_bounds_center_list.append(center)

    return btn_bounds_center_list, list_container_bounds, followed_text


def find_node_with_text(xml_path, text):
    tree = ET.parse(xml_path)
    root = tree.getroot()

    for elem in root.iter(node_tag):
        if elem.attrib["text"] == text:
            return bounds_str_to_center(elem.attrib.get("bounds", ""))
    return []


def bounds_str_to_center(bound):
    left, top, right, bottom = get_bounds(bound)
    center = [(left + right) // 2, (top + bottom) // 2]
    return center


def get_bounds(bound):
    [left_top, right_bottom] = bound.split("][")
    left_top = left_top[1:]
    [left, top] = [str(edge) for edge in left_top.split(",")]
    right_bottom = right_bottom[:-1]
    [right, bottom] = [str(edge) for edge in right_bottom.split(",")]
    return int(left), int(top), int(right), int(bottom)


def exit_with_postprocess():
    subprocess.run("adb shell settings put global animator_duration_scale 1".split())
    if os.path.exists(uiautomator_file_name):
        os.remove(uiautomator_file_name)
    exit(1)


if __name__ == "__main__":
    try_stop_anim = False

    followed_text = ""

    density_result = subprocess.run("adb shell wm density".split(), capture_output=True)
    if "ERROR" in str(density_result.stderr):
        print("Error: can not get screen density, exit")
        exit_with_postprocess()
    density = int(density_result.stdout.split()[-1].decode("utf-8"))
    density_scale = density / 160

    print("Screen density: {}".format(density))

    while True:
        print("Reading UI layout")

        result = subprocess.run(
            "adb shell uiautomator dump --compressed".split(), capture_output=True
        )

        if "ERROR" in str(result.stderr):
            if not try_stop_anim:
                try_stop_anim = True
                print("Warning: error reading UI layout, stop animation and retry")
                subprocess.run(
                    "adb shell settings put global animator_duration_scale 0".split()
                )
                continue
            else:
                print(
                    "Error: tried stopping the animation and returning to retry, still can't get the UI layout, exit"
                )
                exit_with_postprocess()
        try_stop_anim = False

        subprocess.run("adb pull /sdcard/window_dump.xml .".split())
        unfollow_btn_centers, list_container_bounds, followed_text = find_node_bounds(
            uiautomator_file_name, density_scale, followed_text
        )

        if len(list_container_bounds) == 0:
            print("Error: No container for the following user was found")
            exit_with_postprocess()

        if len(unfollow_btn_centers) == 0:
            print("Error: No more followed button was found")
            exit_with_postprocess()

        print("Followed Button center point list: " + str(unfollow_btn_centers))
        for center in unfollow_btn_centers:
            subprocess.run(
                "adb shell input tap {} {}".format(center[0], center[1]).split()
            )
        list_container_h_center = (
            list_container_bounds[0] + list_container_bounds[2]
        ) // 2
        list_container_top = list_container_bounds[1]
        list_container_bottom = list_container_bounds[3]
        # print("list_container_h_center: " + str(list_container_h_center))
        # print("list_container_y_start: " + str(list_container_bottom - 300))
        # print(
        #     "list_container_y_end: "
        #     + str(
        #         list_container_top
        #         + int((list_container_bottom - list_container_top) * 0.63)
        #     )
        # )
        print("Flinging list...")
        subprocess.run(
            "adb shell input swipe {0} {1} {2} {3} 550".format(
                list_container_h_center,
                list_container_bottom - list_container_h_center,
                list_container_h_center,
                list_container_top,
            ).split(" ")
        )
        print(
            "================================================================================"
        )
