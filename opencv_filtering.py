import copy
import math
import os
import statistics
import sys
from pathlib import Path
from typing import NoReturn

import cv2
import numpy as np
from matplotlib import pyplot as plt


class FindFeature:
    def __init__(self, path_reference_feature: str, ccw_90deg_rotation_steps: int = 0) -> NoReturn:
        """
        :param path_reference_feature: supply feature, complete or relative path, with .jpg file ending
        :param ccw_90deg_rotation_steps: if the expected test-picture is rotated you can state that here
        """
        if not Path(path_reference_feature).exists():
            sys.exit(f"Error: input  file '{path_reference_feature}' does not exist")

        self.img_static_objects: np.ndarray = None

        img_01 = cv2.imread(path_reference_feature, 0)
        self.img_ref_raw: np.ndarray = np.rot90(img_01, ccw_90deg_rotation_steps)
        self.img_ref_positive: np.ndarray = self.enhance_details(self.img_ref_raw.copy())
        self.img_ref_negative: np.ndarray = ~self.img_ref_positive.copy()

        self.img_ref_width, self.img_ref_height = self.img_ref_raw.shape[::-1]  # type: int, int
        self.img_ref_radius: int = round(min(self.img_ref_width, self.img_ref_height) / 3)

        self.method: int = cv2.TM_CCORR_NORMED

        self.threshold_positive = 0.60
        self.threshold_negative = 0.70

    def save_reference(self, file_path: str) -> NoReturn:
        """
        Process the reference picture and save it to disk
        :param file_path: complete or relative path, with .jpg file ending
        :return: none
        """
        if file_path[-4:] != ".jpg":
            sys.exit("Error: output file is not specified as jpg")

        img_result = np.vstack((self.img_ref_raw, self.img_ref_positive))
        cv2.imwrite(file_path, img_result, params=[int(cv2.IMWRITE_JPEG_QUALITY), 90])

    def save_find_feature_demo(self, test_file_path: str, save_file_path: str) -> bool:
        """
        Processes test image, find and mark feature if found
        :param test_file_path: path to test image, complete or relative, with file ending
        :param save_file_path: complete or relative path, with .jpg file ending
        :return: True if feature was found
        """
        if not Path(test_file_path).exists():
            sys.exit(f"Error: input  file '{test_file_path}' does not exist")
        if save_file_path[-4:] != ".jpg":
            sys.exit("Error: output file is not specified as jpg")

        # find feature, draw features, save picture
        img_test_raw = cv2.imread(test_file_path, 0)
        img_test_positive = self.enhance_details(img_test_raw.copy())

        matches = self.find_feature(img_test_raw)
        img_test_rect = img_test_raw.copy()
        color = 200
        color_step = min(20.0, color / (len(matches) + 1))

        for match in matches:
            top_left = (match[0], match[1])
            bot_right = (top_left[0] + self.img_ref_width, top_left[1] + self.img_ref_height)
            img_test_rect = cv2.rectangle(
                img_test_raw, top_left, bot_right, color=color, thickness=2
            )
            color -= color_step

        img_result = np.vstack((img_test_positive, img_test_rect))

        cv2.imwrite(save_file_path, img_result, params=[int(cv2.IMWRITE_JPEG_QUALITY), 90])
        return len(matches) > 0

    @staticmethod
    def smooth_vector(input_vector: np.ndarray, neighbor_span: int) -> np.ndarray:
        """
        Running mean with the help of a cumsum
        :param input_vector: 1D Vector
        :param neighbor_span: how far to the left and right you want to go? window_size = (2 * span + 1)
        :return: smoothed version of the vector
        """
        cumsum = np.cumsum(np.insert(input_vector, 0, 0))
        cumsum = np.append(neighbor_span * [cumsum[0]], cumsum)
        cumsum = np.append(cumsum, neighbor_span * [cumsum[-1]])
        window_size = 2 * neighbor_span + 1
        smooth = (cumsum[window_size:] - cumsum[:-window_size]) / float(window_size)
        return smooth

    def enhance_details(self, img_input: np.ndarray, darken_percent: int = 60) -> np.ndarray:
        """
        Exchangeable function that tries to highlight the feature by filtering
        this approach expects an image that biggest surface consists of background
         - find peak in histogram, go down on both sides until one of two things become true
           - current hist-value is larger (rising again)
           - current hist-value is smaller 10% of peak-value (tuning value)
        :param darken_percent: 0 to 100,
        :param img_input: ...
        :return: enhanced image
        """
        if darken_percent < 0 or darken_percent > 100:
            sys.exit("FindFeature.enhance_detail() -> cut_point must be between 0 and 100")
        smooth_span = 2
        histogram = cv2.calcHist([img_input], [0], None, [256], [0, 256])
        histogram = self.smooth_vector(histogram, smooth_span)
        light_peak_position = np.argmax(histogram[:127])
        dark_peak_position = np.argmax(histogram[128:]) + 128

        cut_position = round(
            (dark_peak_position - light_peak_position) * darken_percent / 100 + light_peak_position
        )

        image_mask = np.zeros_like(img_input)
        image_mask[img_input < cut_position] = 255
        return image_mask

    def debug_details(self, img_input: np.ndarray) -> NoReturn:
        """
        Analyze histrogram of current processing pipeline
        :param img_input:
        :return:
        """
        histogram_org = cv2.calcHist([img_input], [0], None, [256], [0, 256])
        plt.plot(histogram_org, label="original")
        histogram_mean = self.smooth_vector(histogram_org, 2)
        plt.plot(histogram_mean, label="mean smoothed")
        gauss_kernel = (7, 7)
        img01 = cv2.GaussianBlur(img_input, gauss_kernel, 0)

        if self.img_static_objects is not None:
            histogram_min = cv2.calcHist([img01], [0], self.img_static_objects, [256], [0, 256])
            plt.plot(histogram_min, label="gauss smoothed without static obj")

        histogram = cv2.calcHist([img01], [0], None, [256], [0, 256])
        plt.plot(histogram, label="gauss smoothed")
        plt.legend(loc="best")
        plt.show()

    @staticmethod
    def get_best_feature(feature_list: list) -> tuple[int, int, float, int, int, float, float]:
        """
        This means the best feature by score (good if you expect one feature per picture)
        :param feature_list: output of find_feature()
        :return: best feature in list
        """
        if len(feature_list) < 1:
            print("Warning: get_nearest_feature was handed an empty feature list")
            return None

        score_highest = feature_list[0][6]
        index_highest = 0
        for index in range(len(feature_list)):
            if feature_list[index][6] > score_highest:
                score_highest = feature_list[index][6]
                index_highest = index
        return feature_list[index_highest]

    def find_feature(
        self,
        img_test_raw: np.ndarray,
        thresholds: tuple[float, float] = None,
        enable_recursion: bool = False,
        recursion_depth: int = 0,
    ) -> list[tuple[int, int, float, int, int, float, float]]:
        """
        Get a list of features on the provided picture
        :param enable_recursion:
        :param img_test_raw:
        :param thresholds: values for positive and negative feature detection
        :param recursion_depth: this fn can call itself, so this value gets incremented
        :return: meta data of features
        """
        img_test_positive = self.enhance_details(img_test_raw)
        img_test_negative = ~img_test_positive.copy()

        # TODO: copyMakeBorder to even find feature (half) out of frame

        img_match_positive = cv2.matchTemplate(
            img_test_positive, self.img_ref_positive, self.method
        )
        img_match_negative = cv2.matchTemplate(
            img_test_negative, self.img_ref_negative, self.method
        )

        if thresholds is None:
            thresholds = (self.threshold_positive, self.threshold_negative)

        list_match_positive = self.extract_matches(img_match_positive, thresholds[0])
        list_match_negative = self.extract_matches(img_match_negative, thresholds[1])

        list_match = list([])
        for match_positive in list_match_positive:
            for index_negative in range(len(list_match_negative)):
                match = (
                    math.fabs(match_positive[0] - list_match_negative[index_negative][0]) <= 4
                ) & (math.fabs(match_positive[1] - list_match_negative[index_negative][1]) <= 4)

                score = match_positive[2] + list_match_negative[index_negative][2]
                if match:
                    feature = (
                        copy.deepcopy(match_positive)
                        + copy.deepcopy(list_match_negative[index_negative])
                        + copy.deepcopy((score,))
                    )
                    list_match.append(copy.deepcopy(feature))
                    list_match_negative.pop(index_negative)
                    break

        if len(list_match) > 0 or recursion_depth >= 5:
            if recursion_depth > 0:
                print(
                    f"   -> found {len(list_match)} features at iteration {recursion_depth} "
                    f"with {np.round(thresholds, 4)} as threshold"
                )
            return list_match
        if enable_recursion:
            print(
                f"-> Warning: found no feature in picture with threshold {np.round(thresholds, 4)}, "
                f"will try again with lower threshold"
            )
            return self.find_feature(
                img_test_raw,
                (thresholds[0] - 0.1, thresholds[1] - 0.1),
                enable_recursion,
                recursion_depth + 1,
            )
        return list_match

    def extract_matches(
        self, img_match: np.ndarray, threshold: float
    ) -> list[tuple[int, int, float]]:
        """
        Find features and extract them as a list
        :param img_match: image
        :param threshold: depending on the method... but it should be between 0 and 1
        :return: meta data of features
        """
        match = True
        match_list = list([])

        while match:
            min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(img_match)

            # saves position and metadata, erases match from map
            top_left = max_loc
            value = max_val
            match = (value >= threshold) * 1
            img_match = cv2.circle(
                img_match, top_left, self.img_ref_radius, color=min_val, thickness=-1
            )

            if match and len(match_list) < 50:
                match_list.append((top_left[0], top_left[1], value))
            else:
                break

        return match_list

    def train_feature_threshold(
        self, image_inp: np.ndarray, expected_features: int = 10
    ) -> NoReturn:
        """
        Depending on the image and feature quality you can try to adapt the thresholds with this fn
        :param image_inp: complete or relative path, with file ending
        :param expected_features:
        :return:
        """

        def sort_key(element: tuple) -> float:
            return element[6]

        matches = self.find_feature(
            image_inp, (0.5, 0.6), enable_recursion=True
        )  # TUNE Threshold until a match is found, TODO: try recursive argument, that lowers the threshold automatically
        reverse = True
        matches.sort(key=sort_key, reverse=reverse)
        matches = matches[: (expected_features + 4)]
        print("found the following feature-matches:")
        print("      x_pos, y_pos, rating_pos, x_neg, y_neg, rating_neg, rating_combined")
        for index in range(len(matches)):
            if index is expected_features:
                print("      === expected features are above ===")
            print(f"-> {index}: {np.round(matches[index], 4)}")

        if len(matches) > expected_features:
            # mean of last known feature and first non-feature + experimental extra 0.1
            self.threshold_positive = (
                matches[expected_features - 1][2] + matches[expected_features][2]
            ) / 2 - 0.1  # TODO: use cumulative value, should be much clearer!
            self.threshold_negative = (
                matches[expected_features - 1][5] + matches[expected_features][5]
            ) / 2 - 0.1
        elif matches and reverse:
            self.threshold_positive = matches[-1][2] - 0.25
            self.threshold_negative = matches[-1][5] - 0.25
        print(
            f"Note: trained feature threshold to pos/neg "
            f"[{round(self.threshold_positive, 4)}; {round(self.threshold_negative, 4)}]"
        )

    def statistics_for_features(self, folder_path: str, expected_features: int = 1) -> NoReturn:
        """
        Get an overview over scores for feature-pics in a special folder. best for pre-sorted stacks of files
        :param folder_path: complete or relative path with "/" termination
        :param expected_features: number of features to expect
        :return:
        """
        if folder_path[-1] != "/":
            print("Error: folder-path has to terminated with a '/'.")
            return

        directories_main = [
            x for x in os.listdir(folder_path) if os.path.isdir(folder_path + x) == False
        ]
        matched_counter = 0
        match_scores = []
        miss_scores = []

        for file_in_dir in directories_main:
            feature_list = self.find_feature(folder_path + file_in_dir)
            if (len(feature_list) >= 1) and (expected_features > 0):
                for match in range(min(len(feature_list), expected_features)):
                    match_scores.append(feature_list[match][6])
                matched_counter += 1
            if len(feature_list) >= (expected_features + 1):
                miss_scores.append(feature_list[expected_features][6])

        print(f"Folder '{folder_path}' had {matched_counter} of {len(directories_main)} matches")
        if len(match_scores) > 0:
            print(
                f" -> match score is {round(min(match_scores), 3)} min, {round(max(match_scores), 3)} max, {round(statistics.mean(match_scores), 3)} mean"
            )
        if len(miss_scores) > 0:
            print(
                f" -> miss  score is {round(min(miss_scores), 3)} min, {round(max(miss_scores), 3)} max, {round(statistics.mean(miss_scores), 3)} mean"
            )

    def train_masking_of_static_objects(self, file_path: str) -> NoReturn:
        """
        Supply an image with soft background
        you can even provide a BW image, color is not important as long as the background is dominating (in size)
        :param file_path: complete or relative path, with file ending
        :return: None
        """
        if not Path(file_path).exists():
            sys.exit(f"Error: file '{file_path}' does not exist")
        self.img_static_objects = None
        img_raw = cv2.imread(file_path, 0)
        img_detail = self.enhance_details(img_raw.copy())
        kernel = np.ones((5, 5), np.uint8)
        self.img_static_objects = ~cv2.dilate(img_detail, kernel, iterations=12)

    def save_masking_of_static_objects(self, file_path: str) -> NoReturn:
        """
        For faster startup you can save the mask
        :param file_path: complete or relative path, with .jpg file ending
        :return: None
        """
        if file_path[-4:] != ".jpg":
            sys.exit("Error: output file is not specified as jpg")
        cv2.imwrite(file_path, self.img_static_objects, params=[int(cv2.IMWRITE_JPEG_QUALITY), 90])


class SheetFilter:
    """
    This Class does the following:
    - look through image and detect 4 Edges of a sheet of paper
    - [maybe] correct orientation, by bringing it to portrait
    - perspective transformation, correct aspect ratio
    - crop to sheet, to remove boarders
    Pre-Condition:
    - feature / Edge must be centered
    """

    def __init__(self, sheet_size: tuple, edge_crop_percent: float = 2):
        self.feature_path = "feature_paper_edge.png"
        self.features = [
            FindFeature(self.feature_path, 0),
            FindFeature(self.feature_path, 1),
            FindFeature(self.feature_path, 2),
            FindFeature(self.feature_path, 3),
        ]
        self.img = None
        self.img_width = 0
        self.img_height = 0
        self.sheet_size = sorted(sheet_size)
        if self.features[0].img_ref_height != self.features[0].img_ref_height:
            sys.exit("Error: the feature must be square (for now)")
        self.feature_offset = self.features[0].img_ref_height / 2
        self.edge_crop = edge_crop_percent / 100

    def open_picture(self, file_path: str) -> NoReturn:
        if not Path(file_path).exists():
            sys.exit(f"Error: input  file '{file_path}' does not exist")

        self.img = cv2.imread(file_path, 0)
        self.img_width, self.img_height = self.img.shape[::-1]  # type: int, int

    def train_feature_threshold(self) -> NoReturn:
        for feature in self.features:
            feature.train_feature_threshold(
                self.img, expected_features=1
            )  # TODO: optimize this. only load file once

    def correct_perspective(self) -> bool:
        corners = list([])
        for feature in self.features:
            matches = feature.find_feature(self.img, enable_recursion=True)
            # TODO: correct to report feature-center
            # TODO: optimize this. only load file once
            best_match = feature.get_best_feature(matches)
            if best_match:
                corners.append(
                    [best_match[0] + self.feature_offset, best_match[1] + self.feature_offset]
                )
            else:
                return False
        # origin (0,0) is upper-left corner, x is horizontal, y is vertical
        length_edge_left = corners[1][1] - corners[0][1]
        length_edge_down = corners[2][0] - corners[1][0]
        length_edge_right = corners[2][1] - corners[3][1]
        length_edge_up = corners[3][0] - corners[0][0]
        length_horizon = length_edge_up + length_edge_down
        length_vertical = length_edge_left + length_edge_right

        if length_horizon > length_vertical:
            # vertical paper
            point_right = round(
                min(self.img_width, self.img_height / self.sheet_size[0] * self.sheet_size[1])
            )
            point_down = round(
                min(self.img_height, point_right / self.sheet_size[1] * self.sheet_size[0])
            )
            ratio_coord = [[0, 0], [0, point_down], [point_right, point_down], [point_right, 0]]
        else:
            # horizontal paper
            point_right = round(
                min(self.img_width, self.img_height / self.sheet_size[1] * self.sheet_size[0])
            )
            point_down = round(
                min(self.img_height, point_right / self.sheet_size[0] * self.sheet_size[1])
            )
            ratio_coord = [[0, 0], [0, point_down], [point_right, point_down], [point_right, 0]]

        pts1 = np.float32(corners)
        pts2 = np.float32(ratio_coord)
        M = cv2.getPerspectiveTransform(pts1, pts2)
        self.img = cv2.warpPerspective(self.img, M, (point_right, point_down))
        self.img_height = point_down
        self.img_width = point_right
        return True

    def crop(self) -> NoReturn:
        crop_width = math.ceil(self.img_width * self.edge_crop)
        crop_height = math.ceil(self.img_height * self.edge_crop)
        # y comes first here
        self.img = self.img[
            crop_height : (self.img_height - crop_height),
            crop_width : (self.img_width - crop_width),
        ]
        self.img_width, self.img_height = self.img.shape[::-1]  # type: int, int

    def enhance_details(self, darken_percent: int):
        self.img = self.features[0].enhance_details(self.img, darken_percent)
        self.img = ~self.img  # inverse, because enhancement defines background as black

    def demo_enhance_details(self) -> NoReturn:
        img_copy = copy.deepcopy(self.img)
        for percent in range(0, 100, 5):
            self.enhance_details(percent)
            self.save(f"demo_enhance_details_{percent}%_darkened.jpg")
            self.img = copy.deepcopy(img_copy)

    def save(self, path: str) -> NoReturn:
        cv2.imwrite(path, self.img, params=[int(cv2.IMWRITE_JPEG_QUALITY), 80])

    def get_dpi(self) -> int:
        sheet_size = sorted(self.sheet_size)
        img_size = sorted(self.img.shape[::-1])
        dpi_short = round(25.4 * img_size[0] / sheet_size[0])
        dpi_long = round(25.4 * img_size[1] / sheet_size[1])
        return max(dpi_short, dpi_long)

    def get_size_mm(self) -> tuple:
        # width is the first parameter
        if self.img_width < self.img_height:
            return tuple(self.sheet_size)
        return self.sheet_size[1], self.sheet_size[0]

    def export_for_tesseract(self) -> np.ndarray:
        img_rgb = cv2.cvtColor(self.img, cv2.COLOR_BGR2RGB)
        return img_rgb

        # self.feat11.save_reference("test_feature.jpg")
        # self.feat00.save_find_feature_demo(file_path, "test_featurefind00.jpg")
        # self.feat10.save_find_feature_demo(file_path, "test_featurefind10.jpg")

        # self.feat01.save_find_feature_demo(file_path, "test_featurefind01.jpg")
