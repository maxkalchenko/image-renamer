"""Tests for the clustering and folder naming in group.py."""

from datetime import datetime, timedelta
import os

import group


def at(day, hour, minute=0):
  return datetime(2026, 11, day, hour, minute)


def test_cluster_by_gap_splits_at_three_hours():
  items = [
    (at(10, 17, 0), "d.png"),
    (at(10, 10, 0), "a.png"),
    (at(10, 13, 59), "c.png"),
    (at(10, 11, 0), "b.png"),
  ]
  groups = group.cluster_by_gap(items, group.GAP)
  assert [[path for _taken_at, path in g] for g in groups] == [
    ["a.png", "b.png", "c.png"],
    ["d.png"],
  ]


def test_cluster_by_gap_splits_on_exact_gap():
  items = [(at(10, 10), "a.png"), (at(10, 13), "b.png")]
  assert len(group.cluster_by_gap(items, group.GAP)) == 2


def test_cluster_by_gap_may_cross_midnight():
  items = [
    (at(10, 23, 0), "a.png"),
    (at(11, 0, 30), "b.png"),
    (at(11, 2, 0), "c.png"),
  ]
  assert len(group.cluster_by_gap(items, group.GAP)) == 1


def test_cluster_by_gap_empty():
  assert group.cluster_by_gap([], group.GAP) == []


def test_folder_name_adds_suffix_when_taken(tmp_path):
  reserved = set()
  assert group.folder_name(tmp_path, at(10, 9), reserved) == "2026-11-10"
  assert group.folder_name(tmp_path, at(10, 20), reserved) == "2026-11-10_2"
  assert group.folder_name(tmp_path, at(10, 23), reserved) == "2026-11-10_3"

  (tmp_path / "2026-11-11").mkdir()
  assert group.folder_name(tmp_path, at(11, 9), reserved) == "2026-11-11_2"


def populate(tmp_path, monkeypatch):
  """Nine photos a minute apart, then two more on a later day."""
  dates = {}
  for index in range(group.MIN_GROUP_SIZE):
    name = f"burst_{index}.png"
    (tmp_path / name).touch()
    dates[name] = at(10, 9) + timedelta(minutes=index)
  for index in range(2):
    name = f"single_{index}.jpg"
    (tmp_path / name).touch()
    dates[name] = at(12, 9) + timedelta(minutes=index)
  (tmp_path / "notes.txt").touch()
  monkeypatch.setattr(
    group, "get_image_date", lambda path: dates[os.path.basename(path)]
  )
  return dates


def test_group_images_dry_run_moves_nothing(tmp_path, monkeypatch, capsys):
  dates = populate(tmp_path, monkeypatch)
  group.group_images(str(tmp_path), dry_run=True)

  assert not (tmp_path / "2026-11-10").exists()
  assert all((tmp_path / name).exists() for name in dates)
  assert "Would move: 9. Kept in place: 2." in capsys.readouterr().out


def test_group_images_moves_large_cluster_only(tmp_path, monkeypatch):
  populate(tmp_path, monkeypatch)
  group.group_images(str(tmp_path))

  moved = sorted(os.listdir(tmp_path / "2026-11-10"))
  assert moved == [f"burst_{index}.png" for index in range(9)]
  assert sorted(os.listdir(tmp_path)) == [
    "2026-11-10",
    "notes.txt",
    "single_0.jpg",
    "single_1.jpg",
  ]
