from io import BytesIO

from cobalt_wren.api.stores import ArtifactWriteRequest
from cobalt_wren.integrations.artifact import S3ArtifactStore


class FakeS3:
    def __init__(self):
        self.items = {}

    def put_object(self, **kwargs):
        if kwargs["Key"] in self.items:
            raise RuntimeError("412 Precondition")
        self.items[kwargs["Key"]] = kwargs

    def get_object(self, **kwargs):
        try:
            item = self.items[kwargs["Key"]]
        except KeyError:
            raise RuntimeError("404 NoSuchKey")
        return {"Body": BytesIO(item["Body"]), "Metadata": item["Metadata"]}

    def list_objects_v2(self, **kwargs):
        return {
            "Contents": [
                {"Key": key} for key in self.items if key.startswith(kwargs["Prefix"])
            ],
            "IsTruncated": False,
        }


def test_s3_artifact_store_round_trip() -> None:
    store = S3ArtifactStore(bucket="bucket", prefix="artifacts", client=FakeS3())
    written = store.put(
        ArtifactWriteRequest(
            run_id=1,
            storage_key="reports/report.json",
            body=b"{}",
            name="report",
            kind="json",
            content_type="application/json",
        )
    )
    read = store.get(written.storage_key)
    assert read is not None and read.body == b"{}"
    assert store.list_for_run(1) == [written]
