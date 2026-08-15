from neo4j import GraphDatabase


class Neo4jWriter:

    RELATIONSHIP_CATEGORIES = {
        'FRIENDS': ['mutual_friends', 'friend_status'],
        #'EDUCATION': ['common_university', 'common_faculty'],
        #'LIKES': ['mutual_likes'],
        #'GROUPS': ['mutual_groups'],
        #'CITY': ['common_city']
    }

    def __init__(self, uri, user, password)->None:
        self.driver = GraphDatabase.driver(uri, auth=(user, password))

    def close(self)->None:
        self.driver.close()

    def write_nodes(self, node_ids: list):
        with self.driver.session() as session:
            for uid in node_ids:
                session.run(
                    "MERGE (u:User {id:$id})",
                    id=uid
                )

    def write_edges(self, edges: list, batch_size: int = 1000):
        """
        Writes edges into Neo4j graph.

        Edge format:
        {
            "source": int,
            "target": int,
            "features": dict
        }
        """

        edges_by_type = {rel_type: [] for rel_type in self.RELATIONSHIP_CATEGORIES}

        for edge in edges:
            source = edge['source']
            target = edge['target']
            features = edge['features']

            for rel_type, keys in self.RELATIONSHIP_CATEGORIES.items():
                if any(features.get(key, 0) for key in keys):
                    sub_features = {key: features.get(key, 0) for key in keys}
                    edges_by_type[rel_type].append({
                        'source': source,
                        'target': target,
                        'features': sub_features
                    })

        with self.driver.session() as session:
            for rel_type, edges_list in edges_by_type.items():
                if not edges_list:
                    continue

                for i in range(0, len(edges_list), batch_size):
                    batch = edges_list[i: i + batch_size]
                    query = f'''
                    UNWIND $batch AS edge
                    MATCH (a:User {{id: edge.source}})
                    MATCH (b:User {{id: edge.target}})
                    MERGE (a)-[r:{rel_type}]-(b)
                    ON CREATE SET r = edge.features, r.symmetric = true
                    ON MATCH SET r += edge.features
                    '''
                    session.run(query=query, batch=batch)

    @staticmethod
    def _create_relationship(tx, source, target, features, rel_type: str)->None:

        query = f"""
        MATCH (a:User {{id: $source}})
        MATCH (b:User {{id: $target}})

        MERGE (a)-[r:{rel_type}]-(b)

        ON CREATE SET r = $features, r.symmetric = true
        ON MATCH SET r += $features
        """

        tx.run(query,
               source=source,
               target=target,
               features=features)