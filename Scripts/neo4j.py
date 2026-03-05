import os
from dotenv import load_dotenv
from Scripts.process_target import load_validate_targets
from Data.features.VKFeatureExtractor import VKFeaturesExtractor
from Database.Neo4j.neo4j_writer import Neo4jWriter

_, vk_ids = load_validate_targets()

def load_graph():

    print("Starting graph loading pipeline...")

    uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    user = os.getenv("NEO4J_USER", "neo4j")
    password = os.getenv("NEO4J_PASSWORD")

    if not password:
        raise ValueError("NEO4J_PASSWORD is not set")

    extractor = VKFeaturesExtractor(users_id=vk_ids)
    writer = Neo4jWriter(uri, user, password)

    try:
        print("Building edge features...")

        edges = extractor.build_edge_features()

        print(f"Edges extracted: {len(edges)}")

        print("Writing edges to Neo4j...")

        writer.write_nodes(node_ids=vk_ids)
        writer.write_edges(edges)

        print("Graph loading completed successfully!")

    finally:
        writer.close()

load_graph()
