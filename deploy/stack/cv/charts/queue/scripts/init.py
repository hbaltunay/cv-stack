import json
import logging
import os

from confluent_kafka.admin import (
    AdminClient,
    AlterConfigOpType,
    ConfigEntry,
    ConfigResource,
    NewPartitions,
    NewTopic,
    ResourceType,
    TopicMetadata,
)

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger("KafkaInit")

BOOTSTRAP = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
CONFIG_FILE = "/queue/kafka_topics.json"


class KafkaAdminManager:
    def __init__(self, bootstrap: str) -> None:
        self.client = AdminClient({"bootstrap.servers": bootstrap})

    def sync(self, config_path: str) -> None:
        if not os.path.exists(config_path):
            raise FileNotFoundError(f"Config file not found at {config_path}")

        with open(config_path) as f:
            data = json.load(f)

        target_topics = data["topics"]
        metadata = self.client.list_topics(timeout=30)
        existing_topics = metadata.topics

        to_create = []
        for t in target_topics:
            name = t["name"]
            if name not in existing_topics:
                logger.info(f"Creating topic: {name}")
                to_create.append(
                    NewTopic(
                        name,
                        num_partitions=t["partitions"],
                        replication_factor=t.get("replication_factor")
                        or t.get("replicationFactor"),
                        config=t["configs"],
                    )
                )
            else:
                logger.info(f"Topic {name} exists, checking for updates...")
                self._update_config_incremental(name, t["configs"])

                self._check_and_increase_partitions(
                    name, t["partitions"], existing_topics[name]
                )

        if to_create:
            fs = self.client.create_topics(to_create)
            for topic, future in fs.items():
                try:
                    future.result()
                    logger.info(f"Successfully created: {topic}")
                except Exception as e:
                    logger.error(f"Failed to create topic {topic}: {e}")

    def _update_config_incremental(
        self, topic_name: str, configs: dict
    ) -> None:
        if not configs:
            return

        entries = []
        for k, v in configs.items():
            if v is None:
                continue

            entry = ConfigEntry(
                name=k,
                value=str(v),
                incremental_operation=AlterConfigOpType.SET,
            )
            entries.append(entry)

        resource = ConfigResource(
            restype=ResourceType.TOPIC,
            name=topic_name,
            incremental_configs=entries,
        )

        try:
            fs = self.client.incremental_alter_configs([resource])
            for res, future in fs.items():
                future.result()
                logger.info(f"Successfully updated configs for: {res.name}")
        except Exception as e:
            logger.error(f"Failed to update configs for {res.name}: {e}")

    def _check_and_increase_partitions(
        self, topic_name: str, target_count: int, topic_metadata: TopicMetadata
    ) -> None:
        current_count = len(topic_metadata.partitions)

        if target_count > current_count:
            logger.info(
                f"Increasing partitions for {topic_name}: {current_count} -> "
                f"{target_count}",
            )
            new_parts = [NewPartitions(topic_name, target_count)]
            fs = self.client.create_partitions(new_parts)

            for topic, future in fs.items():
                try:
                    future.result()
                    logger.info(
                        f"Successfully increased partitions for: {topic}"
                    )
                except Exception as e:
                    logger.error(
                        f"Failed to increase partitions for {topic}: {e}"
                    )
        elif target_count < current_count:
            logger.warning(
                f"Target partitions ({target_count}) is less than current "
                f"({current_count}) for {topic_name}. "
                "Skipping (cannot decrease)."
            )

        else:
            logger.info(
                f"Partition count for {topic_name} is already {target_count}."
                " Skipping."
            )


def main() -> None:
    try:
        manager = KafkaAdminManager(BOOTSTRAP)
        manager.sync(CONFIG_FILE)
    except Exception as e:
        logger.error(f"Failed to sync Kafka topics: {e}")
        exit(1)


if __name__ == "__main__":
    main()
