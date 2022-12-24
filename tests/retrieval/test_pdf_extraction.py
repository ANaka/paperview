import pandas as pd

from paperview.retrieval.pdf_extraction import extract_figure_labels, order_images


def test_order_images():
    # Test ordering of images by page number, then by y0, then by x0
    image_list = [
        {'page_number': 1, 'y0': 10, 'x0': 20},
        {'page_number': 2, 'y0': 15, 'x0': 10},
        {'page_number': 1, 'y0': 5, 'x0': 30},
        {'page_number': 2, 'y0': 20, 'x0': 5},
        {'page_number': 1, 'y0': 5, 'x0': 10},
    ]
    expected_output = [
        {'page_number': 1, 'y0': 5, 'x0': 10, 'image_number': 1},
        {'page_number': 1, 'y0': 5, 'x0': 30, 'image_number': 2},
        {'page_number': 1, 'y0': 10, 'x0': 20, 'image_number': 3},
        {'page_number': 2, 'y0': 15, 'x0': 10, 'image_number': 4},
        {'page_number': 2, 'y0': 20, 'x0': 5, 'image_number': 5},
    ]
    assert order_images(image_list) == expected_output

    # Test that image numbers are added to the image dictionaries
    image_list = [
        {'page_number': 1, 'y0': 10, 'x0': 20},
        {'page_number': 2, 'y0': 15, 'x0': 10},
    ]
    expected_output = [
        {'page_number': 1, 'y0': 10, 'x0': 20, 'image_number': 1},
        {'page_number': 2, 'y0': 15, 'x0': 10, 'image_number': 2},
    ]
    assert order_images(image_list) == expected_output

    # Test empty input
    assert order_images([]) == []

    # Test input with a single image
    image_list = [{'page_number': 1, 'y0': 10, 'x0': 20}]
    expected_output = [{'page_number': 1, 'y0': 10, 'x0': 20, 'image_number': 1}]
    assert order_images(image_list) == expected_output


def test_basic_extraction():
    image = {'page_number': 1, 'top': 0, 'bottom': 100}
    lines = pd.DataFrame(
        [
            {
                'page_number': 1,
                'top': 20,
                'bottom': 30,
                'text': 'Figure 1: This is a label',
                'line_number': 1,
            },
            {
                'page_number': 1,
                'top': 40,
                'bottom': 50,
                'text': 'This is not a label',
                'line_number': 2,
            },
            {
                'page_number': 1,
                'top': 60,
                'bottom': 70,
                'text': 'Fig. 2: This is another label',
                'line_number': 3,
            },
        ]
    )
    expected_output = [
        {'page_number': 1, 'line_number': 1, 'word_number': 0, 'distance': 0.0, 'label': '1'},
        {'page_number': 1, 'line_number': 3, 'word_number': 0, 'distance': 0.0, 'label': '2'},
    ]

    assert extract_figure_labels(image, lines) == expected_output

    # Test label extraction from lines on the next page


def test_next_page_extraction():
    image = {'page_number': 1, 'top': 0, 'bottom': 100}
    lines = pd.DataFrame(
        [
            {
                'page_number': 1,
                'top': 20,
                'bottom': 30,
                'text': 'This is not a label',
                'line_number': 1,
            },
            {
                'page_number': 1,
                'top': 140,
                'bottom': 150,
                'text': 'random text',
                'line_number': 20,
            },
            {
                'page_number': 2,
                'top': 40,
                'bottom': 50,
                'text': 'Fig. 3: This is a label on the next page',
                'line_number': 2,
            },
        ]
    )
    expected_output = [
        {'page_number': 2, 'line_number': 2, 'word_number': 0, 'distance': 95.0, 'label': '3'}
    ]
    print(extract_figure_labels(image, lines))
    assert extract_figure_labels(image, lines) == expected_output
