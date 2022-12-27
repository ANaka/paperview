import click

from paperview.retrieval.biorxiv_api import Article


## click CLI that takes a url, creates an Article instance, and calls `.display_overview`. optional arguments: 'prog_bar' (bool)
@click.command()
@click.argument("url", type=str)
@click.option("--prog_bar", is_flag=True)
def main(url, prog_bar):
    article = Article.from_content_page_url(url, prog_bar=prog_bar)
    article.display_overview()


if __name__ == "__main__":
    main()
