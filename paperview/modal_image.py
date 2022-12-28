import modal

from paperview import repo_root

stub = modal.Stub("paperview_image")

mount = modal.Mount(local_dir=repo_root, remote_dir="/paperview")
image = (
    modal.Image.from_dockerhub('python:3.8-slim')
    .dockerfile_commands(['RUN apt-get update'])
    .apt_install('libmagickwand-dev')
    .run_commands(
        '''sed -i '/domain="coder"/ s/rights="none"/rights="read|write"/' /etc/ImageMagick-6/policy.xml'''
    )
    .copy(mount)
    .pip_install(["/paperview"])
)


if __name__ == '__main__':
    stub.run()
