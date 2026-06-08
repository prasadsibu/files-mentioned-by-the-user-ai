from app.application.services.concall_transcript_service import ConcallTranscriptService


def analyze_concall_transcript(transcript: str) -> dict:
    service = ConcallTranscriptService()
    return service.analyze(transcript).to_api_dict()


if __name__ == "__main__":
    import argparse
    import json
    from pathlib import Path

    parser = argparse.ArgumentParser(description="Analyze a concall transcript with OpenAI.")
    parser.add_argument("transcript_file", help="Path to a transcript text file")
    args = parser.parse_args()

    transcript = Path(args.transcript_file).read_text(encoding="utf-8")
    print(json.dumps(analyze_concall_transcript(transcript), indent=2))
