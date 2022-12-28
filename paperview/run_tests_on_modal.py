import modal
import pytest

from paperview.modal_image import image

stub = modal.Stub("run_paperview_tests")


@stub.function(image=image)
def run_tests():
    pytest.main(['/paperview/tests'])


if __name__ == "__main__":
    with stub.run():
        run_tests()
