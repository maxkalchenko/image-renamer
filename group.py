"""Move root images into date folders when a time cluster has enough files."""

from datetime import timedelta
import os
import sys

from script import VALID_EXTENSIONS, get_image_date, resolve_source_dir

MIN_GROUP_SIZE = 9
GAP = timedelta(hours=3)


def root_images(source_dir):
  """Image files in the source root. Subfolders are left alone."""
  for filename in sorted(os.listdir(source_dir)):
    path = os.path.join(source_dir, filename)
    if os.path.isdir(path):
      continue
    ext = os.path.splitext(filename)[1].lower()
    if ext not in VALID_EXTENSIONS:
      continue
    yield path


def cluster_by_gap(items, gap):
  """Split (datetime, path) pairs when neighbors are `gap` or more apart.

  A cluster may cross midnight when the gap stays under the threshold.
  """
  ordered = sorted(items, key=lambda item: (item[0], os.path.basename(item[1])))
  groups = []
  current = []
  for item in ordered:
    if current and item[0] - current[-1][0] >= gap:
      groups.append(current)
      current = []
    current.append(item)
  if current:
    groups.append(current)
  return groups


def folder_name(source_dir, start, reserved):
  """YYYY-MM-DD from the first photo, then _2, _3, … when that name is taken."""
  date_stamp = start.strftime("%Y-%m-%d")
  candidate = date_stamp
  number = 2
  while candidate in reserved or os.path.exists(
    os.path.join(source_dir, candidate)
  ):
    candidate = f"{date_stamp}_{number}"
    number += 1
  reserved.add(candidate)
  return candidate


def group_images(source_dir, dry_run=False):
  """Move each root cluster of at least MIN_GROUP_SIZE images into a date folder."""
  if not os.path.isdir(source_dir):
    print(f"Error: The path '{source_dir}' does not exist.")
    return

  items = [(get_image_date(path), path) for path in root_images(source_dir)]
  groups = cluster_by_gap(items, GAP)
  reserved = set()
  moved = 0
  kept = 0

  for group in groups:
    start = group[0][0]
    if len(group) < MIN_GROUP_SIZE:
      kept += len(group)
      print(f"Kept in place ({len(group)}): {start.strftime('%Y-%m-%d %H:%M')}")
      continue

    name = folder_name(source_dir, start, reserved)
    folder = os.path.join(source_dir, name)
    print(f"{name}/ ({len(group)} files)")
    for _taken_at, path in group:
      print(f"  {os.path.basename(path)}")
    if dry_run:
      moved += len(group)
      continue

    os.makedirs(folder)
    for _taken_at, path in group:
      os.rename(path, os.path.join(folder, os.path.basename(path)))
    moved += len(group)

  if dry_run:
    print(f"\nDry run. Would move: {moved}. Kept in place: {kept}.")
  else:
    print(f"\nDone! Moved files: {moved}. Kept in place: {kept}.")


def main():
  dry_run = "--dry-run" in sys.argv
  while "--dry-run" in sys.argv:
    sys.argv.remove("--dry-run")
  group_images(resolve_source_dir(), dry_run=dry_run)


if __name__ == "__main__":
  main()
