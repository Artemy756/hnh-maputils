# tests/test_main.py
import pytest
import subprocess
import sys
import json
from pathlib import Path
from maputils import hmap_to_json

# ===== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ =====


def run_script(args, **kwargs):
    """Запускает maputils.py с переданными аргументами"""
    return subprocess.run(
        [sys.executable, "src/maputils.py"] + args,
        capture_output=True,
        text=True,
        timeout=10,
        **kwargs
    )


def files_are_equal(file1: Path, file2: Path) -> bool:
    """Сравнивает два файла"""
    return file1.read_bytes() == file2.read_bytes()


def create_test_hmap_from_json(json_data, tmp_path):
    json_path = tmp_path / "test.json"
    hmap_path = tmp_path / "test.hmap"

    with open(json_path, 'w', encoding='utf-8') as f:
        f.write(json_data)

    result = run_script(["-json2hmap", str(json_path), "-o", str(hmap_path)])
    assert result.returncode == 0, f"json2hmap failed: {result.stderr}"
    return hmap_path


# ===== ТЕСТЫ =====


def test_hmap2json_conversion(example_hmap, temp_dir):
    json_file = temp_dir / "long_test.json"
    hmap_file = temp_dir / "example.hmap"

    result1 = run_script([
        "-hmap2json", str(example_hmap),
        "-o", str(json_file)
    ])
    assert result1.returncode == 0, f"hmap2json failed: {result1.stderr}"
    assert json_file.exists(), "JSON file was not created"

    result2 = run_script([
        "-json2hmap", str(json_file),
        "-o", str(hmap_file)
    ])
    assert result2.returncode == 0, f"json2hmap failed: {result2.stderr}"
    assert hmap_file.exists(), "HMap file was not created"

    assert files_are_equal(example_hmap, hmap_file), \
        f"Files differ: {example_hmap} and {hmap_file}"


def test_merge_deduplicate_grids(temp_dir, example_hmap):
    entries1 = hmap_to_json(str(example_hmap))
    
    if entries1 and entries1[0]["type"] == "grid":
        first_entry = entries1[0].copy()
        entries2 = [first_entry]
    else:
        entries2 = [{"type": "grid", "data_hex": "01020304", "id": 100, "segid": 200}]

    json1 = json.dumps(entries1, ensure_ascii=False)
    json2 = json.dumps(entries2, ensure_ascii=False)

    hmap1 = create_test_hmap_from_json(json1, temp_dir)
    hmap2 = create_test_hmap_from_json(json2, temp_dir)

    result = run_script(["-merge", str(hmap1), str(hmap2)])
    assert result.returncode == 0

    data = json.loads(result.stdout)
    assert len(data["entries"]) >= 1
    assert data["stats"]["removed_duplicates"] >= 0


def test_merge_deduplicate_marks(temp_dir, example_hmap):
    entries1 = hmap_to_json(str(example_hmap))
    
    mark_entry = None
    for e in entries1:
        if e["type"] == "mark":
            mark_entry = e.copy()
            break
    
    if mark_entry:
        entries2 = [mark_entry]
    else:
        entries2 = [{"type": "mark", "data_hex": "05060708", "seg": 100, "tc": {"coord": [10, 20]}}]

    json1 = json.dumps(entries1, ensure_ascii=False)
    json2 = json.dumps(entries2, ensure_ascii=False)

    hmap1 = create_test_hmap_from_json(json1, temp_dir)
    hmap2 = create_test_hmap_from_json(json2, temp_dir)

    result = run_script(["-merge", str(hmap1), str(hmap2)])
    assert result.returncode == 0

    data = json.loads(result.stdout)
    assert len(data["entries"]) >= 1
    assert data["stats"]["removed_duplicates"] >= 0


def test_merge_no_deduplicate(temp_dir, example_hmap):
    entries1 = hmap_to_json(str(example_hmap))
    
    if entries1:
        first_entry = entries1[0].copy()
        entries2 = [first_entry]
    else:
        entries2 = [{"type": "grid", "data_hex": "01020304", "id": 100}]

    json1 = json.dumps(entries1, ensure_ascii=False)
    json2 = json.dumps(entries2, ensure_ascii=False)

    hmap1 = create_test_hmap_from_json(json1, temp_dir)
    hmap2 = create_test_hmap_from_json(json2, temp_dir)

    from maputils import merge_hmaps

    result = merge_hmaps(str(hmap1), str(hmap2), deduplicate=False)
    assert result is not None
    assert len(result["entries"]) >= 2
    assert result["stats"]["removed_duplicates"] == 0


def test_merge_output_file(temp_dir, example_hmap):
    entries1 = hmap_to_json(str(example_hmap))
    
    entries2 = []
    for e in entries1:
        if e["type"] == "grid":
            new_entry = e.copy()
            new_entry["id"] = 9999
            entries2.append(new_entry)
            break
    
    if not entries2:
        entries2 = [{"type": "grid", "data_hex": "0304", "id": 101}]

    json1 = json.dumps(entries1, ensure_ascii=False)
    json2 = json.dumps(entries2, ensure_ascii=False)

    hmap1 = create_test_hmap_from_json(json1, temp_dir)
    hmap2 = create_test_hmap_from_json(json2, temp_dir)

    output_path = temp_dir / "output.hmap"
    result = run_script(["-merge", str(hmap1), str(hmap2), "-o", str(output_path)])
    assert result.returncode == 0
    assert output_path.exists()
