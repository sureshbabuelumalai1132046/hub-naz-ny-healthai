import logging
import argparse

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def prepend_explain(file: str) -> str:
    """
    This method takes a query or list of queries separated by a semicolon and prepends an EXPLAIN statement to each query.
    Args:
        file: The file containing the queries.
    Returns:
        queries: The file with the EXPLAIN statement prepended to each query.
    """

    # split the file into a list of queries and prepend EXPLAIN to each query
    queries = [f"EXPLAIN {q.strip()}" for q in file.split(";") if q.strip()]

    # join the queries back together
    queries = ";\n\n".join(queries)

    if not queries.endswith(";"):
        queries += ";"  # add a semicolon to the end of the last query

    return queries


if __name__ == "__main__":

    args = argparse.ArgumentParser()
    args.add_argument(
        "--path_to_file",
        type=str,
        required=True,
        help="The file containing the queries.",
    )
    args = args.parse_args()

    # open the file
    with open(args.path_to_file, "r") as file:
        queries = file.read()

    # add explain to statements
    queries = prepend_explain(queries)

    # write the queries back to the file
    with open(args.path_to_file, "w") as file:
        file.write(queries)

    logger.info(f"Changed file {args.path_to_file}")