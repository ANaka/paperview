import modal
import pytest

from paperview import repo_root
from paperview.modal_image import image
from paperview.retrieval.biorxiv_api import Article

stub = modal.Stub("run_paperview_tests")


@stub.function(image=image)
def run_tests():
    pytest.main(['/paperview/tests'])


if __name__ == "__main__":
    with stub.run():
        run_tests()
