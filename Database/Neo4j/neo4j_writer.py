from neo4j import GraphDatabase


class Neo4jWriter:

    def __init__(self, uri, user, password):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))

    def close(self):
        self.driver.close()

    def write_nodes(self, node_ids: list):
        with self.driver.session() as session:
            for uid in node_ids:
                session.run(
                    "MERGE (u:User {id:$id})",
                    id=uid
                )

    def write_edges(self, edges: list):
        """
        Writes edges into Neo4j graph.

        Edge format:
        {
            "source": int,
            "target": int,
            "features": dict
        }
        """

        with self.driver.session() as session:
            for edge in edges:
                if not self._edge_valid(edge["features"]):
                    continue

                session.execute_write(
                    self._create_relationship,
                    edge["source"],
                    edge["target"],
                    edge["features"]
                )

    def _edge_valid(self, features: dict) -> bool:
        """
        Edge exists if at least one feature > 0
        """

        return any(
            isinstance(v, (int, float)) and v > 0
            for v in features.values()
        )

    @staticmethod
    def _create_relationship(tx, source, target, features):

        query = """
        MATCH (a:User {id: $source})
        MATCH (b:User {id: $target})

        MERGE (a)-[r:CONNECTED]-(b)

        ON CREATE SET r = $features, r.symmetric = true
        ON MATCH SET r += $features
        """

        tx.run(query,
               source=source,
               target=target,
               features=features)