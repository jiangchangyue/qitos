import tempfile
import unittest
from pathlib import Path

from qitos.benchmark import normalize_benchmark_name, resolve_builtin_runner
from qitos.benchmark.cybergym import CyberGymBenchmarkAdapter, make_trace_writer, task_slug
from qitos.recipes.benchmarks import cybergym


class CybergymRecipeTests(unittest.TestCase):
    def test_task_slug_replaces_colon(self):
        self.assertEqual(task_slug("arvo:1065"), "arvo_1065")
        self.assertEqual(task_slug("oss-fuzz:42535201"), "oss-fuzz_42535201")

    def test_make_trace_writer_uses_prefix_and_task_slug(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            writer = make_trace_writer(
                trace_logdir=tmpdir,
                trace_prefix="qitos_cybergym",
                task_id="arvo:1065",
                model_id="GLM-5.1-sii",
            )

            self.assertTrue(writer.run_id.startswith("qitos_cybergym_arvo_1065_"))
            self.assertEqual(writer.metadata["model_id"], "GLM-5.1-sii")
            self.assertTrue(Path(writer.run_dir).exists())

    def test_adapter_builds_qitos_task_from_task_id(self):
        adapter = CyberGymBenchmarkAdapter()

        task = adapter.to_task({"task_id": "arvo:1065"}, split="level1", idx=0)

        self.assertEqual(task.id, "arvo:1065")
        self.assertEqual(task.inputs["difficulty"], "level1")
        self.assertEqual(task.metadata["benchmark"], "cybergym")

    def test_cybergym_is_registered_as_benchmark_family(self):
        self.assertEqual(normalize_benchmark_name("cybergym"), "cybergym")
        self.assertIsNotNone(resolve_builtin_runner(benchmark="cybergym", strategy="smoke"))

    def test_recipe_reuses_benchmark_family_helpers(self):
        self.assertIs(cybergym.task_slug, task_slug)
        self.assertIs(cybergym.make_trace_writer, make_trace_writer)


if __name__ == "__main__":
    unittest.main()
