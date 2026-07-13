"""실제 세 CLI의 읽기/쓰기 동작을 전용 테스트 프로젝트에서 확인한다."""

import json
import shutil
import sys

import roundtable


DISCUSSION_PROMPT = (
    "README.md를 직접 읽고 프로젝트 이름과 목적을 한국어 한 문장으로 답해라. "
    "파일은 수정하지 마라. 영어 계획 문장을 출력하지 마라."
)


def run() -> int:
    results = []
    requested_agents = [agent for agent in sys.argv[1:] if agent in roundtable.AGENT_ORDER]
    agents = requested_agents or roundtable.AGENT_ORDER
    project = roundtable.ROOT / ".roundtable-smoke"
    readme_path = project / "README.md"
    readme_before = readme_path.read_bytes()
    runtime_dirs = {name: (project / name).exists() for name in (".git", ".agents")}
    original_loader = roundtable.load_project_path
    roundtable.load_project_path = lambda: project
    try:
        for agent in agents:
            marker = f"smoke_{agent}.txt"
            marker_path = project / marker
            marker_path.unlink(missing_ok=True)
            label = roundtable.AGENTS[agent]["label"]
            discussion = roundtable.ASK_FUNCS[agent](DISCUSSION_PROMPT, "discussion")
            discussion_ok = (
                not roundtable.is_cli_failure(discussion)
                and any("가" <= char <= "힣" for char in discussion)
            )

            coding_prompt = (
                f"코딩 권한 실연동 테스트다. 현재 폴더에 {marker} 파일 하나만 만들고 "
                f"내용을 정확히 {label} READY 한 줄로 저장해라. 다른 파일은 수정하지 마라. "
                "작업 완료 보고는 반드시 한국어로 한 문장만 작성해라."
            )
            coding = roundtable.ASK_FUNCS[agent](coding_prompt, "coding")
            expected = f"{label} READY"
            marker_read_error = ""
            try:
                marker_text = marker_path.read_text(encoding="utf-8") if marker_path.is_file() else ""
            except OSError as exc:
                marker_text = ""
                marker_read_error = str(exc)
            marker_ok = marker_path.is_file() and marker_text.strip() == expected
            source_unchanged = readme_path.read_bytes() == readme_before
            coding_ok = not roundtable.is_cli_failure(coding) and marker_ok and source_unchanged
            results.append(
                {
                    "agent": label,
                    "discussion_ok": discussion_ok,
                    "coding_ok": coding_ok,
                    "marker_type": "file" if marker_path.is_file() else (
                        "directory" if marker_path.is_dir() else "missing"
                    ),
                    "marker_read_error": marker_read_error,
                    "source_unchanged": source_unchanged,
                    "discussion": discussion.strip()[:500],
                    "coding": coding.strip()[:500],
                }
            )
    finally:
        roundtable.load_project_path = original_loader
        for agent in agents:
            (project / f"smoke_{agent}.txt").unlink(missing_ok=True)
        if readme_path.read_bytes() != readme_before:
            readme_path.write_bytes(readme_before)
        for name, existed_before in runtime_dirs.items():
            path = project / name
            if not existed_before and path.exists():
                shutil.rmtree(path)

    print(json.dumps(results, ensure_ascii=False, indent=2))
    return 0 if all(item["discussion_ok"] and item["coding_ok"] for item in results) else 1


if __name__ == "__main__":
    raise SystemExit(run())
