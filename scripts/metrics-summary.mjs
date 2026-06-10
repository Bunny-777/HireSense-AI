import fs from "node:fs";
import path from "node:path";
import process from "node:process";

const metricsPath = process.argv[2]
  ? path.resolve(process.cwd(), process.argv[2])
  : path.resolve(process.cwd(), "metrics.jsonl");

function readMetrics(filePath) {
  if (!fs.existsSync(filePath)) {
    throw new Error(`Metrics file not found: ${filePath}`);
  }

  const raw = fs.readFileSync(filePath, "utf8").trim();
  if (!raw) {
    return [];
  }

  return raw
    .split("\n")
    .map((line, index) => {
      try {
        return JSON.parse(line);
      } catch (error) {
        throw new Error(`Invalid JSON on line ${index + 1}: ${error.message}`);
      }
    });
}

function average(values) {
  if (values.length === 0) {
    return 0;
  }
  return values.reduce((sum, value) => sum + value, 0) / values.length;
}

function percentile(values, fraction) {
  if (values.length === 0) {
    return 0;
  }
  const sorted = [...values].sort((a, b) => a - b);
  const index = Math.min(sorted.length - 1, Math.floor(sorted.length * fraction));
  return sorted[index];
}

function summarize(records) {
  const recordings = records.map((record) => Number(record.recording_seconds || 0));
  const transcription = records.map((record) => Number(record.transcription_ms || 0));
  const followups = records.map((record) => Number(record.followup_ms || 0));

  const longestTranscript = records.reduce((current, record) => {
    const transcript = String(record.transcript || "");
    return transcript.length > current.length ? transcript : current;
  }, "");

  return {
    totalTurns: records.length,
    avgRecordingSeconds: average(recordings),
    avgTranscriptionMs: average(transcription),
    avgFollowupMs: average(followups),
    p95FollowupMs: percentile(followups, 0.95),
    longestTranscriptChars: longestTranscript.length,
    latestResponse: records.at(-1)?.response || "n/a"
  };
}

function printSummary(summary, filePath) {
  console.log(`HireSense metrics summary`);
  console.log(`Source: ${filePath}`);
  console.log(`Turns: ${summary.totalTurns}`);
  console.log(`Avg recording seconds: ${summary.avgRecordingSeconds.toFixed(2)}`);
  console.log(`Avg transcription ms: ${summary.avgTranscriptionMs.toFixed(2)}`);
  console.log(`Avg follow-up ms: ${summary.avgFollowupMs.toFixed(2)}`);
  console.log(`P95 follow-up ms: ${summary.p95FollowupMs.toFixed(2)}`);
  console.log(`Longest transcript chars: ${summary.longestTranscriptChars}`);
  console.log(`Latest interviewer response: ${summary.latestResponse}`);
}

try {
  const records = readMetrics(metricsPath);
  if (records.length === 0) {
    console.log(`No metrics found in ${metricsPath}`);
    process.exit(0);
  }

  printSummary(summarize(records), metricsPath);
} catch (error) {
  console.error(error.message);
  process.exit(1);
}
