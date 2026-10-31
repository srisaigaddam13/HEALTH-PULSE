"""
HealthPulse – Symptom Tracking System (Cyber-Clinical Edition)
Author: HealthPulse Educational Team
Description: A unique, feature-packed Python web application to log, track,
             and monitor health symptoms in a separate browser window.
             Featuring an interactive Anatomical Body Map, Wong-Baker Pain Scale,
             Dual-Channel ECG Telemetry Monitor, Web Audio Cardiac Vitals,
             and Persistent JSON Storage.
Dependencies: Python standard library only (http.server, urllib, json, os, datetime, socket, webbrowser).
"""

import datetime
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import os
import socket
import sys
import urllib.parse
import webbrowser

DATA_FILE = "symptoms.json"
REPORT_FILE = "health_report.txt"
CSV_FILE = "symptoms.csv"
DISCLAIMER = "For personal tracking only; not a substitute for professional medical advice."


# ============================================================================
# DATA PERSISTENCE & ANALYTICS HELPERS
# ============================================================================

def load_data(filepath=DATA_FILE):
    """Load symptom records from JSON file. Returns [] on missing/corrupted file."""
    if not os.path.exists(filepath):
        return []
    try:
        with open(filepath, "r", encoding="utf-8") as file:
            data = json.load(file)
            return data if isinstance(data, list) else []
    except (json.JSONDecodeError, OSError) as error:
        print(f"Warning: Could not read '{filepath}' ({error}). Starting with an empty list.")
        return []


def save_data(records, filepath=DATA_FILE):
    """Save records list to JSON file with indentation."""
    try:
        with open(filepath, "w", encoding="utf-8") as file:
            json.dump(records, file, indent=4)
        return True
    except OSError as error:
        print(f"Error saving data to '{filepath}': {error}")
        return False


def get_next_id(records):
    """Generate next auto-increment integer ID."""
    return max([r.get("id", 0) for r in records], default=0) + 1


def build_summary(records):
    """Compute summary statistics, 7-day trend analysis, and formatted report text."""
    if not records:
        return {
            "total_entries": 0,
            "unique_symptoms": 0,
            "overall_avg": 0.0,
            "most_frequent": "None",
            "most_frequent_count": 0,
            "most_severe": None,
            "breakdown": {},
            "recent_count": 0,
            "recent_avg": 0.0,
            "vitality_score": 100,
            "trend_message": "No symptom data logged yet.",
            "trend_status": "none",
            "report_text": "No symptom records found. Add symptoms to generate a summary.",
            "disclaimer": DISCLAIMER
        }

    total_entries = len(records)
    unique_symptoms = len({r["symptom"].lower() for r in records})
    overall_avg = sum(r["severity"] for r in records) / total_entries

    # Vitality Score (0-100%): 100 minus weighted average severity
    vitality_score = max(10, min(100, int(100 - (overall_avg * 7.5))))

    # Group counts and severities per symptom
    symptom_stats = {}
    for r in records:
        name = r["symptom"].lower()
        if name not in symptom_stats:
            symptom_stats[name] = {"count": 0, "total_sev": 0}
        symptom_stats[name]["count"] += 1
        symptom_stats[name]["total_sev"] += r["severity"]

    most_freq_name, most_freq_data = max(symptom_stats.items(), key=lambda x: x[1]["count"])
    most_severe_entry = max(records, key=lambda r: r["severity"])

    # 7-day recent analysis
    today = datetime.date.today()
    seven_days_ago = today - datetime.timedelta(days=7)
    recent_records = []
    for r in records:
        try:
            if datetime.datetime.strptime(r["date"], "%Y-%m-%d").date() >= seven_days_ago:
                recent_records.append(r)
        except (ValueError, KeyError):
            continue

    recent_count = len(recent_records)
    recent_avg = (sum(r["severity"] for r in recent_records) / recent_count) if recent_count > 0 else 0.0

    if recent_count > 0:
        diff = recent_avg - overall_avg
        if diff > 0.5:
            trend_msg = f"WORSE than overall average (+{diff:.2f}). Recent symptom intensity has spiked."
            trend_status = "worse"
        elif diff < -0.5:
            trend_msg = f"BETTER than overall average ({diff:.2f}). Symptoms are improving over the past week!"
            trend_status = "improving"
        else:
            trend_msg = "STABLE (consistent with your overall baseline)."
            trend_status = "stable"
    else:
        trend_msg = "No symptoms logged in the past 7 days."
        trend_status = "none"

    # Build formatted text report
    lines = [
        "=" * 68,
        "          HEALTHPULSE CYBER-CLINICAL - HEALTH SUMMARY REPORT",
        f"          Generated: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "=" * 68,
        f"* Total Logged Entries    : {total_entries}",
        f"* Unique Symptoms Tracked : {unique_symptoms}",
        f"* Overall Average Severity: {overall_avg:.2f} / 10",
        f"* Health Vitality Index   : {vitality_score}%",
        f"* Most Frequent Symptom   : '{most_freq_name}' ({most_freq_data['count']} occurrence(s))",
        f"* Peak Severity Incident  : '{most_severe_entry['symptom']}' "
        f"(Severity: {most_severe_entry['severity']}/10, Date: {most_severe_entry['date']})"
    ]
    if most_severe_entry.get("notes"):
        lines.append(f"  Incident Notes          : {most_severe_entry['notes']}")

    lines.extend(["\n" + "-" * 68, f"{'Symptom':<26} {'Occurrences':<15} {'Avg Severity':<15}", "-" * 68])
    breakdown_dict = {}
    for sym_name, stats in sorted(symptom_stats.items()):
        avg_sev = stats["total_sev"] / stats["count"]
        breakdown_dict[sym_name] = {"count": stats["count"], "avg_severity": round(avg_sev, 2)}
        lines.append(f"{sym_name.capitalize():<26} {stats['count']:<15} {avg_sev:.2f}/10")
    lines.append("-" * 68)

    lines.append("\n--- 7-Day Vitals & Severity Trends ---")
    if recent_count > 0:
        lines.append(f"* Active entries in 7 days: {recent_count}")
        lines.append(f"* 7-day average severity  : {recent_avg:.2f} / 10")
        lines.append(f"* Trend Evaluation        : {trend_msg}")
    else:
        lines.append("* No symptom entries recorded in the past 7 days.")

    lines.extend(["\n" + "=" * 68, f"DISCLAIMER: {DISCLAIMER}", "=" * 68])
    report_text = "\n".join(lines)

    return {
        "total_entries": total_entries,
        "unique_symptoms": unique_symptoms,
        "overall_avg": round(overall_avg, 2),
        "vitality_score": vitality_score,
        "most_frequent": most_freq_name,
        "most_frequent_count": most_freq_data["count"],
        "most_severe": most_severe_entry,
        "breakdown": breakdown_dict,
        "recent_count": recent_count,
        "recent_avg": round(recent_avg, 2),
        "trend_message": trend_msg,
        "trend_status": trend_status,
        "report_text": report_text,
        "disclaimer": DISCLAIMER
    }


def generate_csv(records):
    """Generate RFC 4180 CSV string for all records."""
    headers = ["id", "date", "symptom", "severity", "notes"]
    lines = [",".join(headers)]
    for r in sorted(records, key=lambda x: (x.get("date", ""), x.get("id", 0))):
        symptom = r.get("symptom", "").replace('"', '""')
        notes = (r.get("notes") or "").replace('"', '""')
        lines.append(f'{r.get("id")},{r.get("date")},"{symptom}",{r.get("severity")},"{notes}"')
    return "\n".join(lines)


# ============================================================================
# EMBEDDED FRONTEND (CYBER-CLINICAL UI + INTERACTIVE BODY MAP + DUAL ECG)
# ============================================================================

HTML_CONTENT = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>HealthPulse – Cyber-Clinical Telemetry & Symptom Tracker</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <style>
    @keyframes heartbeat {
      0%, 100% { transform: scale(1); filter: drop-shadow(0 0 0 rgba(244,63,94,0)); }
      15% { transform: scale(1.22); filter: drop-shadow(0 0 10px rgba(244,63,94,0.6)); }
      30% { transform: scale(1.02); filter: drop-shadow(0 0 2px rgba(244,63,94,0.2)); }
      45% { transform: scale(1.15); filter: drop-shadow(0 0 8px rgba(244,63,94,0.5)); }
      60% { transform: scale(1); }
    }
    .heart-beat {
      animation: heartbeat 1.25s infinite ease-in-out;
    }
    body {
      background-color: #060913;
      color: #f1f5f9;
      font-family: system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    }
    /* Oscilloscope glow grid */
    .telemetry-screen {
      background: radial-gradient(circle at center, rgba(16, 185, 129, 0.04) 0%, rgba(6, 9, 19, 0.95) 100%);
      box-shadow: inset 0 0 30px rgba(0, 0, 0, 0.8), 0 0 15px rgba(16, 185, 129, 0.1);
    }
    /* Custom scrollbars */
    ::-webkit-scrollbar { width: 6px; height: 6px; }
    ::-webkit-scrollbar-track { background: #0b1120; }
    ::-webkit-scrollbar-thumb { background: #334155; border-radius: 3px; }
    ::-webkit-scrollbar-thumb:hover { background: #475569; }
    /* Body Map Hotspots */
    .body-part {
      cursor: pointer;
      transition: all 0.25s ease;
      fill: #1e293b;
      stroke: #334155;
    }
    .body-part:hover, .body-part.active {
      fill: #0284c7;
      stroke: #38bdf8;
      filter: drop-shadow(0 0 8px rgba(56, 189, 248, 0.7));
    }
  </style>
</head>
<body class="min-h-screen flex flex-col justify-between p-3 sm:p-6 lg:p-8 relative overflow-x-hidden selection:bg-rose-500/30">

  <!-- FULL-SCREEN ANIMATED MEDICAL CANVAS (DYNAMIC PHOSPHOR ECG & AMBIENT PARTICLES) -->
  <canvas id="medicalCanvas" class="fixed inset-0 pointer-events-none w-full h-full z-0 opacity-40"></canvas>

  <div class="max-w-6xl w-full mx-auto relative z-10 space-y-6">

    <!-- TOP TELEMETRY COMMAND HEADER -->
    <header class="flex flex-col md:flex-row items-start md:items-center justify-between gap-4 p-5 rounded-2xl bg-slate-900/90 border border-slate-800/90 backdrop-blur-xl shadow-2xl">
      <div class="flex items-center gap-3.5">
        <div class="w-13 h-13 p-3 rounded-2xl bg-rose-500/10 border border-rose-500/30 flex items-center justify-center text-rose-500 text-2xl heart-beat shadow-inner">
          ♥
        </div>
        <div>
          <div class="flex items-center gap-2.5">
            <h1 class="text-xl font-black tracking-tight text-white flex items-center gap-2">
              HealthPulse <span class="text-xs font-mono px-2 py-0.5 rounded bg-sky-500/15 text-sky-400 border border-sky-500/30 font-semibold">OS v2.0</span>
            </h1>
            <span class="hidden sm:inline-flex px-2 py-0.5 text-[11px] font-semibold rounded-full bg-emerald-500/15 text-emerald-400 border border-emerald-500/30 items-center gap-1.5">
              <span class="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-ping"></span>
              Live Telemetry
            </span>
          </div>
          <p class="text-xs text-slate-400 mt-0.5">Clinical-Grade Symptom Logging & Biometric Health Analytics</p>
        </div>
      </div>

      <!-- Telemetry Vitals & Audio Beeper Toggle -->
      <div class="flex flex-wrap items-center gap-3 self-stretch md:self-auto justify-between md:justify-end">
        <div class="flex items-center gap-4 bg-slate-950/70 px-3.5 py-2 rounded-xl border border-slate-800">
          <div>
            <div class="text-[10px] text-slate-500 font-mono uppercase tracking-wider">Heart Rate</div>
            <div class="text-sm font-bold text-rose-400 flex items-center gap-1">
              <span class="inline-block w-2 h-2 rounded-full bg-rose-500 animate-pulse"></span>
              <span id="bpmVal">72</span> <span class="text-[10px] text-slate-400 font-normal">BPM</span>
            </div>
          </div>
          <div class="w-px h-6 bg-slate-800"></div>
          <div>
            <div class="text-[10px] text-slate-500 font-mono uppercase tracking-wider">SpO2</div>
            <div class="text-sm font-bold text-sky-400">99%</div>
          </div>
          <div class="w-px h-6 bg-slate-800"></div>
          <div>
            <div class="text-[10px] text-slate-500 font-mono uppercase tracking-wider">Rhythm</div>
            <div class="text-xs font-bold text-emerald-400">Sinus Norm</div>
          </div>
        </div>

        <!-- Audio Toggle Button -->
        <button id="soundToggleBtn" onclick="toggleCardiacAudio()"
                class="px-3 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 text-xs font-medium flex items-center gap-1.5 transition">
          <span id="soundIcon">🔇</span>
          <span id="soundLabel">Audio Muted</span>
        </button>
      </div>
    </header>

    <!-- KEY STATS & HEALTH VITALITY GAUGES -->
    <div class="grid grid-cols-2 lg:grid-cols-4 gap-4">
      <div class="p-4 rounded-2xl bg-slate-900/80 border border-slate-800/80 backdrop-blur-md relative overflow-hidden">
        <div class="flex items-center justify-between text-xs text-slate-400 font-medium">
          <span>TOTAL LOGS</span>
          <span class="text-slate-500 text-sm">📋</span>
        </div>
        <div id="statTotal" class="text-3xl font-black text-white mt-1.5">0</div>
        <div class="text-[11px] text-slate-500 mt-1">Stored persistently in symptoms.json</div>
      </div>

      <div class="p-4 rounded-2xl bg-slate-900/80 border border-slate-800/80 backdrop-blur-md relative overflow-hidden">
        <div class="flex items-center justify-between text-xs text-slate-400 font-medium">
          <span>UNIQUE SYMPTOMS</span>
          <span class="text-sky-400 text-sm">🧬</span>
        </div>
        <div id="statUnique" class="text-3xl font-black text-sky-400 mt-1.5">0</div>
        <div class="text-[11px] text-slate-500 mt-1" id="statUniqueSub">Distinct tracked conditions</div>
      </div>

      <div class="p-4 rounded-2xl bg-slate-900/80 border border-slate-800/80 backdrop-blur-md relative overflow-hidden">
        <div class="flex items-center justify-between text-xs text-slate-400 font-medium">
          <span>AVG SEVERITY</span>
          <span class="text-amber-400 text-sm">⚡</span>
        </div>
        <div id="statAvg" class="text-3xl font-black text-amber-400 mt-1.5">0.00 <span class="text-xs text-slate-400 font-normal">/ 10</span></div>
        <div class="text-[11px] text-slate-500 mt-1">Across all historical records</div>
      </div>

      <div class="p-4 rounded-2xl bg-slate-900/80 border border-slate-800/80 backdrop-blur-md relative overflow-hidden">
        <div class="flex items-center justify-between text-xs text-slate-400 font-medium">
          <span>7-DAY TREND</span>
          <span id="trendIcon" class="text-emerald-400 text-sm">📈</span>
        </div>
        <div id="statTrend" class="text-lg font-bold text-emerald-400 mt-2 flex items-center gap-1.5">
          <span>● Stable</span>
        </div>
        <div class="text-[11px] text-slate-500 mt-1" id="statTrendSub">Recent vs. baseline severity</div>
      </div>
    </div>

    <!-- MAIN INTERACTIVE SECTION: BODY MAP & LOGGING CONSOLE -->
    <div class="grid grid-cols-1 lg:grid-cols-12 gap-6">

      <!-- LEFT: ANATOMICAL BODY MAP & QUICK-LOG PILLS (5 COLS) -->
      <div class="lg:col-span-5 p-5 rounded-2xl bg-slate-900/85 border border-slate-800/90 backdrop-blur-xl space-y-4">
        <div class="flex items-center justify-between border-b border-slate-800 pb-3">
          <div>
            <h2 class="text-xs font-bold text-white uppercase tracking-wider flex items-center gap-1.5">
              <span>🧍</span> Anatomical Symptom Locator
            </h2>
            <p class="text-[11px] text-slate-400">Click a body region to pre-select symptoms</p>
          </div>
          <span id="activeRegionBadge" class="text-[10px] font-mono px-2 py-0.5 rounded bg-sky-500/15 text-sky-400 border border-sky-500/30">Select Area</span>
        </div>

        <!-- Stylized Interactive Anatomical SVG -->
        <div class="flex justify-center items-center py-2 relative">
          <svg viewBox="0 0 200 320" class="w-44 h-64 filter drop-shadow">
            <!-- Head / Cranial -->
            <path id="part-head" class="body-part" onclick="selectBodyPart('head', 'headache')"
                  d="M100 20 C85 20 85 45 85 52 C85 64 92 72 100 72 C108 72 115 64 115 52 C115 45 115 20 100 20 Z" />
            <!-- Neck & Throat -->
            <path id="part-throat" class="body-part" onclick="selectBodyPart('throat', 'sore throat')"
                  d="M93 72 L107 72 L109 82 L91 82 Z" />
            <!-- Chest & Respiratory -->
            <path id="part-chest" class="body-part" onclick="selectBodyPart('chest', 'cough')"
                  d="M74 84 L126 84 L122 130 L78 130 Z" />
            <!-- Abdomen & Digestive -->
            <path id="part-abdomen" class="body-part" onclick="selectBodyPart('abdomen', 'nausea')"
                  d="M78 132 L122 132 L118 175 L82 175 Z" />
            <!-- Left Arm -->
            <path id="part-left-arm" class="body-part" onclick="selectBodyPart('left-arm', 'joint pain')"
                  d="M72 86 L56 125 L50 165 L57 167 L65 130 L74 95 Z" />
            <!-- Right Arm -->
            <path id="part-right-arm" class="body-part" onclick="selectBodyPart('right-arm', 'joint pain')"
                  d="M128 86 L144 125 L150 165 L143 167 L135 130 L126 95 Z" />
            <!-- Pelvis & Lower Back -->
            <path id="part-pelvis" class="body-part" onclick="selectBodyPart('pelvis', 'back pain')"
                  d="M82 177 L118 177 L124 200 L76 200 Z" />
            <!-- Left Leg -->
            <path id="part-left-leg" class="body-part" onclick="selectBodyPart('left-leg', 'muscle fatigue')"
                  d="M78 202 L96 202 L92 255 L88 300 L76 300 L74 255 Z" />
            <!-- Right Leg -->
            <path id="part-right-leg" class="body-part" onclick="selectBodyPart('right-leg', 'muscle fatigue')"
                  d="M104 202 L122 202 L126 255 L124 300 L112 300 L108 255 Z" />
          </svg>

          <!-- Floating Info Callout -->
          <div class="absolute bottom-2 left-2 text-[10px] text-slate-500 bg-slate-950/80 px-2 py-1 rounded border border-slate-800">
            Interactive Bio-Map
          </div>
        </div>

        <!-- Quick Tap Symptom Pills -->
        <div class="space-y-1.5">
          <div class="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">Quick Select Symptoms</div>
          <div class="flex flex-wrap gap-1.5">
            <button type="button" onclick="quickFillSymptom('headache', 6)" class="px-2.5 py-1 text-xs rounded-lg bg-slate-800/80 hover:bg-slate-700 text-slate-200 border border-slate-700/60 transition">Headache</button>
            <button type="button" onclick="quickFillSymptom('migraine', 8)" class="px-2.5 py-1 text-xs rounded-lg bg-slate-800/80 hover:bg-slate-700 text-rose-300 border border-slate-700/60 transition">Migraine</button>
            <button type="button" onclick="quickFillSymptom('fatigue', 5)" class="px-2.5 py-1 text-xs rounded-lg bg-slate-800/80 hover:bg-slate-700 text-slate-200 border border-slate-700/60 transition">Fatigue</button>
            <button type="button" onclick="quickFillSymptom('cough', 4)" class="px-2.5 py-1 text-xs rounded-lg bg-slate-800/80 hover:bg-slate-700 text-slate-200 border border-slate-700/60 transition">Cough</button>
            <button type="button" onclick="quickFillSymptom('fever', 7)" class="px-2.5 py-1 text-xs rounded-lg bg-slate-800/80 hover:bg-slate-700 text-amber-300 border border-slate-700/60 transition">Fever</button>
            <button type="button" onclick="quickFillSymptom('nausea', 6)" class="px-2.5 py-1 text-xs rounded-lg bg-slate-800/80 hover:bg-slate-700 text-slate-200 border border-slate-700/60 transition">Nausea</button>
            <button type="button" onclick="quickFillSymptom('back pain', 5)" class="px-2.5 py-1 text-xs rounded-lg bg-slate-800/80 hover:bg-slate-700 text-slate-200 border border-slate-700/60 transition">Back Pain</button>
          </div>
        </div>
      </div>

      <!-- RIGHT: LOG SYMPTOM CONSOLE & REAL-TIME TELEMETRY HUD (7 COLS) -->
      <div class="lg:col-span-7 space-y-5">
        
        <!-- DUAL-CHANNEL TELEMETRY OSCILLOSCOPE MONITOR -->
        <div class="p-4 rounded-2xl telemetry-screen border border-emerald-500/30 relative overflow-hidden space-y-2">
          <div class="flex items-center justify-between text-xs font-mono text-emerald-400">
            <span class="flex items-center gap-1.5">
              <span class="w-2 h-2 rounded-full bg-emerald-400 animate-ping"></span>
              LEAD II &bull; CARDIAC RHYTHM OSCILLOSCOPE
            </span>
            <span class="text-[11px] text-emerald-500/80 font-mono">25mm/s &bull; 10mm/mV</span>
          </div>

          <canvas id="telemetryCanvas" class="w-full h-24 rounded-lg bg-slate-950/80 border border-emerald-500/20"></canvas>
        </div>

        <!-- QUICK SYMPTOM LOGGING CONSOLE FORM -->
        <div class="p-5 rounded-2xl bg-slate-900/85 border border-slate-800/90 backdrop-blur-xl space-y-4 shadow-xl">
          <div class="flex items-center justify-between border-b border-slate-800 pb-3">
            <div>
              <h2 class="text-sm font-bold text-white uppercase tracking-wider">Fast Symptom Logger</h2>
              <p class="text-xs text-slate-400">Validated entries are saved directly to symptoms.json</p>
            </div>
            <span class="text-xs font-mono px-2.5 py-1 rounded bg-slate-800 text-slate-300">Option 1</span>
          </div>

          <form id="quickLogForm" onsubmit="handleQuickSubmit(event)" class="space-y-4">
            <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label class="block text-xs font-medium text-slate-300 mb-1">Symptom Name <span class="text-rose-400">*</span></label>
                <input type="text" id="quickSymptom" required placeholder="e.g. headache, fatigue"
                       class="w-full px-3 py-2 rounded-lg bg-slate-800/90 border border-slate-700 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-rose-500 transition-colors" />
              </div>

              <div>
                <label class="block text-xs font-medium text-slate-300 mb-1">Date (YYYY-MM-DD)</label>
                <input type="date" id="quickDate" required
                       class="w-full px-3 py-2 rounded-lg bg-slate-800/90 border border-slate-700 text-sm text-white focus:outline-none focus:border-rose-500" />
              </div>
            </div>

            <!-- WONG-BAKER PAIN RATING SCALE -->
            <div>
              <div class="flex justify-between items-center mb-1">
                <label class="text-xs font-medium text-slate-300">Severity Rating (1-10)</label>
                <div id="painScaleDisplay" class="flex items-center gap-1.5 px-2.5 py-0.5 rounded-lg border text-xs font-bold bg-amber-500/20 text-amber-400 border-amber-500/30">
                  <span id="painEmoji" class="text-sm">😐</span>
                  <span id="painLabel">5/10 - Moderate Discomfort</span>
                </div>
              </div>
              <input type="range" id="quickSeverity" min="1" max="10" value="5"
                     class="w-full accent-rose-500 cursor-pointer" oninput="updatePainScale(this.value)" />
              <div class="flex justify-between text-[10px] text-slate-500 font-mono mt-1">
                <span>1 (Mild 😊)</span>
                <span>5 (Moderate 😐)</span>
                <span>10 (Severe 😭)</span>
              </div>
            </div>

            <div>
              <label class="block text-xs font-medium text-slate-300 mb-1">Clinical Notes (Optional)</label>
              <input type="text" id="quickNotes" placeholder="e.g. triggered after bright sunlight, resolved with hydration"
                     class="w-full px-3 py-2 rounded-lg bg-slate-800/90 border border-slate-700 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-rose-500" />
            </div>

            <button type="submit"
                    class="w-full py-2.5 px-4 rounded-xl bg-gradient-to-r from-rose-600 to-rose-500 hover:from-rose-500 hover:to-rose-400 text-white font-bold text-xs uppercase tracking-wider transition shadow-lg shadow-rose-600/30 flex items-center justify-center gap-2">
              <span>+</span> Record Health Symptom
            </button>
          </form>
        </div>

      </div>

    </div>

    <!-- SYMPTOMS LOG TABLE, SEARCH & FILTER CONTROLS -->
    <div class="rounded-2xl bg-slate-900/85 border border-slate-800/90 backdrop-blur-xl overflow-hidden shadow-2xl">
      
      <!-- Filter Bar -->
      <div class="p-4 border-b border-slate-800 flex flex-col md:flex-row items-stretch md:items-center justify-between gap-3">
        <div class="flex items-center gap-2 flex-1">
          <div class="relative flex-1 max-w-md">
            <span class="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-500 text-xs">🔍</span>
            <input type="text" id="searchInput" placeholder="Search symptoms by keyword..."
                   class="w-full pl-8 pr-3 py-2 text-xs rounded-xl bg-slate-800/80 border border-slate-700 text-white placeholder-slate-500 focus:outline-none focus:border-rose-500" />
          </div>

          <!-- Severity Quick Filter Chips -->
          <div class="hidden sm:flex items-center gap-1 text-xs">
            <button onclick="setFilter('all')" id="filter-all" class="px-2.5 py-1.5 rounded-lg bg-slate-800 text-white font-medium border border-slate-700">All</button>
            <button onclick="setFilter('mild')" id="filter-mild" class="px-2.5 py-1.5 rounded-lg text-emerald-400 hover:bg-slate-800/60 font-medium">Mild (1-3)</button>
            <button onclick="setFilter('moderate')" id="filter-moderate" class="px-2.5 py-1.5 rounded-lg text-amber-400 hover:bg-slate-800/60 font-medium">Mod (4-6)</button>
            <button onclick="setFilter('severe')" id="filter-severe" class="px-2.5 py-1.5 rounded-lg text-rose-400 hover:bg-slate-800/60 font-medium">Severe (7-10)</button>
          </div>
        </div>

        <!-- Action Exports -->
        <div class="flex items-center gap-2">
          <button onclick="openSummaryModal()"
                  class="px-3.5 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 text-xs font-semibold flex items-center gap-1.5 transition">
            <span>📊</span> Summary Report
          </button>
          <button onclick="exportTXT()"
                  class="px-3 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 text-xs font-medium flex items-center gap-1 transition">
            <span>📄</span> TXT
          </button>
          <button onclick="exportCSV()"
                  class="px-3 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-emerald-400 border border-slate-700 text-xs font-medium flex items-center gap-1 transition">
            <span>📊</span> CSV
          </button>
        </div>
      </div>

      <!-- Table Body -->
      <div class="overflow-x-auto">
        <table class="w-full text-left text-xs">
          <thead class="bg-slate-800/50 text-slate-400 uppercase font-medium border-b border-slate-800 text-[11px]">
            <tr>
              <th class="py-3 px-4">ID</th>
              <th class="py-3 px-4">Date</th>
              <th class="py-3 px-4">Symptom Name</th>
              <th class="py-3 px-4">Severity &amp; Pain Level</th>
              <th class="py-3 px-4">Clinical Notes</th>
              <th class="py-3 px-4 text-right">Actions</th>
            </tr>
          </thead>
          <tbody id="symptomsTableBody" class="divide-y divide-slate-800/70 font-sans">
            <!-- Dynamically populated via JS -->
          </tbody>
        </table>
      </div>

      <div id="emptyState" class="py-12 text-center text-slate-400 hidden">
        <div class="text-3xl mb-2">📋</div>
        <p class="text-sm font-medium">No symptoms match the current filter.</p>
        <p class="text-xs text-slate-500 mt-1">Select a body part above or click "+ Record Health Symptom".</p>
      </div>
    </div>

    <!-- CLINICAL DISCLAIMER FOOTER -->
    <footer class="p-4 rounded-2xl bg-slate-900/60 border border-slate-800 text-xs text-slate-400 flex items-center gap-3">
      <span class="text-amber-400 font-bold text-base">ℹ</span>
      <span><strong>Medical Notice:</strong> HealthPulse is for personal tracking only; not a substitute for professional medical advice, clinical diagnosis, or emergency care.</span>
    </footer>

  </div>

  <!-- EDIT RECORD MODAL -->
  <div id="editModal" class="fixed inset-0 z-50 bg-black/75 backdrop-blur-sm flex items-center justify-center p-4 hidden">
    <div class="w-full max-w-md rounded-2xl bg-slate-900 border border-slate-800 p-6 shadow-2xl space-y-4">
      <div class="flex items-center justify-between border-b border-slate-800 pb-3">
        <h3 id="editModalTitle" class="text-sm font-bold text-white uppercase tracking-wider">Update Symptom Record</h3>
        <button onclick="closeEditModal()" class="text-slate-400 hover:text-white text-lg">&times;</button>
      </div>

      <form id="editForm" onsubmit="handleEditSubmit(event)" class="space-y-4">
        <input type="hidden" id="editId">

        <div>
          <label class="block text-xs font-medium text-slate-300 mb-1">Symptom</label>
          <input type="text" id="editSymptom" required class="w-full px-3 py-2 rounded-lg bg-slate-800 border border-slate-700 text-sm text-white focus:outline-none focus:border-rose-500">
        </div>

        <div>
          <label class="block text-xs font-medium text-slate-300 mb-1">Severity (1-10): <span id="editSevVal" class="text-rose-400 font-bold">5</span></label>
          <input type="range" id="editSeverity" min="1" max="10" value="5" class="w-full accent-rose-500" oninput="document.getElementById('editSevVal').textContent = this.value">
        </div>

        <div>
          <label class="block text-xs font-medium text-slate-300 mb-1">Date</label>
          <input type="date" id="editDate" required class="w-full px-3 py-2 rounded-lg bg-slate-800 border border-slate-700 text-sm text-white focus:outline-none focus:border-rose-500">
        </div>

        <div>
          <label class="block text-xs font-medium text-slate-300 mb-1">Notes</label>
          <input type="text" id="editNotes" class="w-full px-3 py-2 rounded-lg bg-slate-800 border border-slate-700 text-sm text-white focus:outline-none focus:border-rose-500">
        </div>

        <div class="flex justify-end gap-2 pt-2 border-t border-slate-800">
          <button type="button" onclick="closeEditModal()" class="px-4 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-medium">Cancel</button>
          <button type="submit" class="px-4 py-2 rounded-lg bg-rose-600 hover:bg-rose-500 text-white text-xs font-bold">Update Record</button>
        </div>
      </form>
    </div>
  </div>

  <!-- SUMMARY REPORT MODAL -->
  <div id="summaryModal" class="fixed inset-0 z-50 bg-black/80 backdrop-blur-md flex items-center justify-center p-4 hidden">
    <div class="w-full max-w-2xl rounded-2xl bg-slate-900 border border-slate-800 p-6 shadow-2xl space-y-4 max-h-[90vh] overflow-y-auto">
      <div class="flex items-center justify-between border-b border-slate-800 pb-3">
        <h3 class="text-sm font-bold text-white uppercase tracking-wider flex items-center gap-2">
          <span>📊</span> HealthPulse Telemetry Summary Report
        </h3>
        <button onclick="closeSummaryModal()" class="text-slate-400 hover:text-white text-lg">&times;</button>
      </div>

      <div class="p-4 rounded-xl bg-slate-950 border border-slate-800 font-mono text-xs text-slate-300 whitespace-pre-wrap leading-relaxed select-all" id="summaryReportPre">
        Loading summary...
      </div>

      <div class="flex justify-end gap-2 pt-2 border-t border-slate-800">
        <button onclick="exportTXT()" class="px-4 py-2 rounded-xl bg-rose-600 hover:bg-rose-500 text-white text-xs font-bold flex items-center gap-1.5">
          <span>💾</span> Download TXT
        </button>
        <button onclick="exportCSV()" class="px-4 py-2 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-bold flex items-center gap-1.5">
          <span>📊</span> Download CSV
        </button>
        <button onclick="closeSummaryModal()" class="px-4 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-medium">Close</button>
      </div>
    </div>
  </div>

  <!-- TOAST NOTIFICATION -->
  <div id="toast" class="fixed bottom-6 right-6 z-50 px-4 py-3 rounded-xl bg-slate-800 border border-slate-700 text-white text-xs font-medium shadow-2xl transition-all duration-300 transform translate-y-12 opacity-0 pointer-events-none flex items-center gap-2">
    <span id="toastIcon">✓</span>
    <span id="toastMsg">Action completed</span>
  </div>

  <script>
    let symptomsData = [];
    let currentFilter = 'all';

    // Set default date to today
    document.getElementById("quickDate").value = new Date().toISOString().split("T")[0];

    // Web Audio API: Cardiac Telemetry Beeper (Synthetic oscillator, zero audio files required)
    let audioCtx = null;
    let soundEnabled = false;

    function toggleCardiacAudio() {
      soundEnabled = !soundEnabled;
      const label = document.getElementById("soundLabel");
      const icon = document.getElementById("soundIcon");
      const btn = document.getElementById("soundToggleBtn");

      if (soundEnabled) {
        if (!audioCtx) audioCtx = new (window.AudioContext || window.webkitAudioContext)();
        label.textContent = "Audio Active";
        icon.textContent = "🔊";
        btn.className = "px-3 py-2 rounded-xl bg-emerald-500/20 text-emerald-400 border border-emerald-500/40 text-xs font-medium flex items-center gap-1.5 transition";
        playBeep();
      } else {
        label.textContent = "Audio Muted";
        icon.textContent = "🔇";
        btn.className = "px-3 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 text-xs font-medium flex items-center gap-1.5 transition";
      }
    }

    function playBeep(freq = 880, duration = 0.07) {
      if (!soundEnabled) return;
      try {
        if (!audioCtx) audioCtx = new (window.AudioContext || window.webkitAudioContext)();
        if (audioCtx.state === 'suspended') audioCtx.resume();
        const osc = audioCtx.createOscillator();
        const gain = audioCtx.createGain();
        osc.type = "sine";
        osc.frequency.setValueAtTime(freq, audioCtx.currentTime);
        gain.gain.setValueAtTime(0.04, audioCtx.currentTime);
        gain.gain.exponentialRampToValueAtTime(0.0001, audioCtx.currentTime + duration);
        osc.connect(gain);
        gain.connect(audioCtx.destination);
        osc.start();
        osc.stop(audioCtx.currentTime + duration);
      } catch (e) {
        // Audio policy ignore
      }
    }

    // Toast UI
    function showToast(msg, isError = false) {
      const toast = document.getElementById("toast");
      const toastMsg = document.getElementById("toastMsg");
      const toastIcon = document.getElementById("toastIcon");

      toastMsg.textContent = msg;
      toastIcon.textContent = isError ? "⚠" : "✓";
      toast.className = `fixed bottom-6 right-6 z-50 px-4 py-3 rounded-xl text-white text-xs font-medium shadow-2xl transition-all duration-300 transform translate-y-0 opacity-100 flex items-center gap-2 ${isError ? 'bg-rose-950 border border-rose-700' : 'bg-slate-800 border border-emerald-500/50'}`;

      setTimeout(() => {
        toast.className = "fixed bottom-6 right-6 z-50 px-4 py-3 rounded-xl bg-slate-800 border border-slate-700 text-white text-xs font-medium shadow-2xl transition-all duration-300 transform translate-y-12 opacity-0 pointer-events-none flex items-center gap-2";
      }, 3000);
    }

    // Pain Rating Scale helper (Wong-Baker Scale)
    function updatePainScale(val) {
      val = parseInt(val);
      const display = document.getElementById("painScaleDisplay");
      const emoji = document.getElementById("painEmoji");
      const label = document.getElementById("painLabel");

      if (val <= 2) {
        emoji.textContent = "😊";
        label.textContent = `${val}/10 - Minimal / Mild`;
        display.className = "flex items-center gap-1.5 px-2.5 py-0.5 rounded-lg border text-xs font-bold bg-emerald-500/20 text-emerald-400 border-emerald-500/30";
      } else if (val <= 4) {
        emoji.textContent = "🙂";
        label.textContent = `${val}/10 - Noticeable Discomfort`;
        display.className = "flex items-center gap-1.5 px-2.5 py-0.5 rounded-lg border text-xs font-bold bg-teal-500/20 text-teal-400 border-teal-500/30";
      } else if (val <= 6) {
        emoji.textContent = "😐";
        label.textContent = `${val}/10 - Moderate Pain`;
        display.className = "flex items-center gap-1.5 px-2.5 py-0.5 rounded-lg border text-xs font-bold bg-amber-500/20 text-amber-400 border-amber-500/30";
      } else if (val <= 8) {
        emoji.textContent = "😣";
        label.textContent = `${val}/10 - Severe Discomfort`;
        display.className = "flex items-center gap-1.5 px-2.5 py-0.5 rounded-lg border text-xs font-bold bg-orange-500/20 text-orange-400 border-orange-500/30";
      } else {
        emoji.textContent = "😭";
        label.textContent = `${val}/10 - Intense / Disabling`;
        display.className = "flex items-center gap-1.5 px-2.5 py-0.5 rounded-lg border text-xs font-bold bg-rose-500/20 text-rose-400 border-rose-500/30";
      }
    }

    // Anatomical Body Map selection
    function selectBodyPart(partId, suggestedSymptom) {
      document.querySelectorAll(".body-part").forEach(el => el.classList.remove("active"));
      const target = document.getElementById(`part-${partId}`);
      if (target) target.classList.add("active");

      document.getElementById("activeRegionBadge").textContent = partId.toUpperCase();
      document.getElementById("quickSymptom").value = suggestedSymptom;
      document.getElementById("quickSymptom").focus();
      playBeep(980, 0.05);
      showToast(`Selected ${partId} region: Suggested '${suggestedSymptom}'`);
    }

    function quickFillSymptom(name, severity) {
      document.getElementById("quickSymptom").value = name;
      document.getElementById("quickSeverity").value = severity;
      updatePainScale(severity);
      playBeep(840, 0.04);
      showToast(`Filled '${name}' (Severity: ${severity})`);
    }

    // Data Load & REST calls
    async function loadSymptoms() {
      try {
        const res = await fetch("/api/symptoms");
        symptomsData = await res.json();
        renderTable();
        loadSummary();
      } catch (err) {
        showToast("Error loading records from server", true);
      }
    }

    async function loadSummary() {
      try {
        const res = await fetch("/api/summary");
        const s = await res.json();
        document.getElementById("statTotal").textContent = s.total_entries;
        document.getElementById("statUnique").textContent = s.unique_symptoms;
        document.getElementById("statAvg").innerHTML = `${s.overall_avg.toFixed(2)} <span class="text-xs text-slate-400 font-normal">/ 10</span>`;

        const trendEl = document.getElementById("statTrend");
        const trendIcon = document.getElementById("trendIcon");
        if (s.trend_status === "improving") {
          trendEl.className = "text-lg font-bold text-emerald-400 mt-2 flex items-center gap-1.5";
          trendEl.innerHTML = "<span>↓ Improving</span>";
          trendIcon.textContent = "📉";
        } else if (s.trend_status === "worse") {
          trendEl.className = "text-lg font-bold text-rose-400 mt-2 flex items-center gap-1.5";
          trendEl.innerHTML = "<span>↑ Worsening</span>";
          trendIcon.textContent = "📈";
        } else {
          trendEl.className = "text-lg font-bold text-sky-400 mt-2 flex items-center gap-1.5";
          trendEl.innerHTML = "<span>● Stable</span>";
          trendIcon.textContent = "📊";
        }
        document.getElementById("statTrendSub").textContent = `${s.recent_count} log(s) in last 7 days`;
      } catch (err) {
        console.error(err);
      }
    }

    function setFilter(filter) {
      currentFilter = filter;
      ['all', 'mild', 'moderate', 'severe'].forEach(f => {
        const btn = document.getElementById(`filter-${f}`);
        if (btn) {
          if (f === filter) {
            btn.className = "px-2.5 py-1.5 rounded-lg bg-slate-800 text-white font-medium border border-slate-700 shadow-sm";
          } else {
            btn.className = "px-2.5 py-1.5 rounded-lg text-slate-400 hover:bg-slate-800/60 font-medium";
          }
        }
      });
      renderTable();
    }

    function renderTable() {
      const tbody = document.getElementById("symptomsTableBody");
      const emptyState = document.getElementById("emptyState");
      const query = document.getElementById("searchInput").value.trim().toLowerCase();

      let filtered = symptomsData.slice();

      // Severity range filter
      if (currentFilter === 'mild') filtered = filtered.filter(r => r.severity <= 3);
      else if (currentFilter === 'moderate') filtered = filtered.filter(r => r.severity >= 4 && r.severity <= 6);
      else if (currentFilter === 'severe') filtered = filtered.filter(r => r.severity >= 7);

      // Search keyword filter
      if (query) {
        filtered = filtered.filter(r => r.symptom.toLowerCase().includes(query) || (r.notes && r.notes.toLowerCase().includes(query)));
      }

      // Chronological sort
      filtered.sort((a, b) => (b.date || "").localeCompare(a.date || "") || (b.id - a.id));

      tbody.innerHTML = "";
      if (filtered.length === 0) {
        emptyState.classList.remove("hidden");
        return;
      }
      emptyState.classList.add("hidden");

      filtered.forEach(rec => {
        const tr = document.createElement("tr");
        tr.className = "hover:bg-slate-800/40 transition-colors";

        let sevClass = "bg-emerald-500/15 text-emerald-400 border-emerald-500/30";
        let painFace = "😊 Mild";
        if (rec.severity >= 7) {
          sevClass = "bg-rose-500/15 text-rose-400 border-rose-500/30";
          painFace = "😭 Severe";
        } else if (rec.severity >= 4) {
          sevClass = "bg-amber-500/15 text-amber-400 border-amber-500/30";
          painFace = "😐 Moderate";
        }

        tr.innerHTML = `
          <td class="py-3 px-4 font-mono text-slate-500">#${rec.id}</td>
          <td class="py-3 px-4 font-mono text-slate-300 whitespace-nowrap">${rec.date}</td>
          <td class="py-3 px-4 font-semibold text-white capitalize flex items-center gap-2">
            <span class="w-1.5 h-1.5 rounded-full ${rec.severity >= 7 ? 'bg-rose-500' : (rec.severity >= 4 ? 'bg-amber-500' : 'bg-emerald-500')}"></span>
            ${rec.symptom}
          </td>
          <td class="py-3 px-4 whitespace-nowrap">
            <span class="px-2.5 py-0.5 rounded-lg border font-bold text-xs ${sevClass}">
              ${rec.severity}/10 &bull; ${painFace}
            </span>
          </td>
          <td class="py-3 px-4 text-slate-300 max-w-xs truncate">${rec.notes || '<span class="text-slate-600">-</span>'}</td>
          <td class="py-3 px-4 text-right space-x-1 whitespace-nowrap">
            <button onclick="openEditModal(${rec.id})" class="px-2.5 py-1 rounded-lg bg-slate-800 hover:bg-slate-700 text-sky-400 text-xs transition">Edit</button>
            <button onclick="deleteRecord(${rec.id})" class="px-2.5 py-1 rounded-lg bg-slate-800 hover:bg-rose-900/50 text-rose-400 text-xs transition">Delete</button>
          </td>
        `;
        tbody.appendChild(tr);
      });
    }

    document.getElementById("searchInput").addEventListener("input", renderTable);

    // Form Submissions
    async function handleQuickSubmit(e) {
      e.preventDefault();
      const symptom = document.getElementById("quickSymptom").value.trim().toLowerCase();
      const severity = parseInt(document.getElementById("quickSeverity").value);
      const date = document.getElementById("quickDate").value;
      const notes = document.getElementById("quickNotes").value.trim();

      try {
        const res = await fetch("/api/symptoms", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ symptom, severity, date, notes })
        });
        if (res.ok) {
          playBeep(1040, 0.08);
          showToast(`Logged symptom: '${symptom}' (${severity}/10)`);
          document.getElementById("quickSymptom").value = "";
          document.getElementById("quickNotes").value = "";
          loadSymptoms();
        }
      } catch (err) {
        showToast("Error saving record", true);
      }
    }

    function openEditModal(id) {
      const rec = symptomsData.find(r => r.id === id);
      if (!rec) return;
      document.getElementById("editId").value = rec.id;
      document.getElementById("editSymptom").value = rec.symptom;
      document.getElementById("editSeverity").value = rec.severity;
      document.getElementById("editSevVal").textContent = rec.severity;
      document.getElementById("editDate").value = rec.date;
      document.getElementById("editNotes").value = rec.notes || "";
      document.getElementById("editModal").classList.remove("hidden");
    }

    function closeEditModal() {
      document.getElementById("editModal").classList.add("hidden");
    }

    async function handleEditSubmit(e) {
      e.preventDefault();
      const id = parseInt(document.getElementById("editId").value);
      const symptom = document.getElementById("editSymptom").value.trim().toLowerCase();
      const severity = parseInt(document.getElementById("editSeverity").value);
      const date = document.getElementById("editDate").value;
      const notes = document.getElementById("editNotes").value.trim();

      try {
        const res = await fetch("/api/symptoms", {
          method: "PUT",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ id, symptom, severity, date, notes })
        });
        if (res.ok) {
          closeEditModal();
          showToast(`Record #${id} updated`);
          loadSymptoms();
        }
      } catch (err) {
        showToast("Error updating record", true);
      }
    }

    async function deleteRecord(id) {
      const rec = symptomsData.find(r => r.id === id);
      const name = rec ? rec.symptom : id;
      if (!confirm(`Are you sure you want to delete symptom #${id} ('${name}')?`)) return;

      try {
        const res = await fetch(`/api/symptoms?id=${id}`, { method: "DELETE" });
        if (res.ok) {
          showToast(`Record #${id} deleted`);
          loadSymptoms();
        }
      } catch (err) {
        showToast("Error deleting record", true);
      }
    }

    async function openSummaryModal() {
      try {
        const res = await fetch("/api/summary");
        const s = await res.json();
        document.getElementById("summaryReportPre").textContent = s.report_text;
        document.getElementById("summaryModal").classList.remove("hidden");
      } catch (err) {
        showToast("Error loading summary report", true);
      }
    }

    function closeSummaryModal() {
      document.getElementById("summaryModal").classList.add("hidden");
    }

    async function exportTXT() {
      try {
        const res = await fetch("/api/export", { method: "POST" });
        const d = await res.json();
        showToast(d.message);

        const blob = new Blob([d.report_text], { type: "text/plain;charset=utf-8" });
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = "health_report.txt";
        a.click();
        URL.revokeObjectURL(url);
      } catch (err) {
        showToast("Export error", true);
      }
    }

    async function exportCSV() {
      try {
        const res = await fetch("/api/export/csv");
        const text = await res.text();
        showToast("CSV report generated!");

        const blob = new Blob([text], { type: "text/csv;charset=utf-8" });
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = "symptoms.csv";
        a.click();
        URL.revokeObjectURL(url);
      } catch (err) {
        showToast("CSV export error", true);
      }
    }

    // ==========================================
    // DUAL-CHANNEL TELEMETRY OSCILLOSCOPE
    // ==========================================
    const teleCanvas = document.getElementById("telemetryCanvas");
    const teleCtx = teleCanvas.getContext("2d");

    function resizeTele() {
      teleCanvas.width = teleCanvas.clientWidth;
      teleCanvas.height = teleCanvas.clientHeight;
    }
    resizeTele();
    window.addEventListener("resize", resizeTele);

    let teleX = 0;
    const teleHistory = [];

    function renderTelemetry() {
      teleCtx.fillStyle = "rgba(6, 9, 19, 0.2)";
      teleCtx.fillRect(0, 0, teleCanvas.width, teleCanvas.height);

      // Grid dots
      teleCtx.fillStyle = "rgba(16, 185, 129, 0.15)";
      for (let x = 0; x < teleCanvas.width; x += 20) {
        for (let y = 0; y < teleCanvas.height; y += 20) {
          teleCtx.fillRect(x, y, 1, 1);
        }
      }

      teleX = (teleX + 2.2) % teleCanvas.width;
      const midY = teleCanvas.height * 0.55;
      const pos = teleX % 240;
      let y = midY;

      // Realistic ECG pattern
      if (pos > 25 && pos < 45) { // P
        y -= Math.sin((pos - 25) / 20 * Math.PI) * 7;
      } else if (pos >= 52 && pos < 57) { // Q
        y += 6;
      } else if (pos >= 57 && pos < 65) { // R
        y -= 36;
      } else if (pos >= 65 && pos < 72) { // S
        y += 14;
      } else if (pos > 95 && pos < 135) { // T
        y -= Math.sin((pos - 95) / 40 * Math.PI) * 11;
      }

      // Cardiac beep on R wave peak
      if (Math.floor(pos) === 60) {
        playBeep(880, 0.06);
      }

      teleHistory.push({ x: teleX, y });
      while (teleHistory.length > teleCanvas.width * 0.9) teleHistory.shift();

      if (teleHistory.length > 1) {
        teleCtx.beginPath();
        teleCtx.strokeStyle = "#10b981";
        teleCtx.lineWidth = 1.8;
        teleCtx.shadowColor = "#10b981";
        teleCtx.shadowBlur = 8;
        for (let i = 1; i < teleHistory.length; i++) {
          if (Math.abs(teleHistory[i].x - teleHistory[i - 1].x) > 30) continue;
          teleCtx.moveTo(teleHistory[i - 1].x, teleHistory[i - 1].y);
          teleCtx.lineTo(teleHistory[i].x, teleHistory[i].y);
        }
        teleCtx.stroke();
        teleCtx.shadowBlur = 0;
      }

      // Sweep Beam
      teleCtx.fillStyle = "#34d399";
      teleCtx.beginPath();
      teleCtx.arc(teleX, y, 2.5, 0, Math.PI * 2);
      teleCtx.fill();

      requestAnimationFrame(renderTelemetry);
    }
    renderTelemetry();

    // ==========================================
    // FULL-SCREEN ANIMATED MEDICAL CANVAS BACKGROUND
    // ==========================================
    const bgCanvas = document.getElementById("medicalCanvas");
    const bgCtx = bgCanvas.getContext("2d");

    function resizeBg() {
      bgCanvas.width = window.innerWidth;
      bgCanvas.height = window.innerHeight;
    }
    resizeBg();
    window.addEventListener("resize", resizeBg);

    const bgParticles = [];
    for (let i = 0; i < 30; i++) {
      bgParticles.push({
        x: Math.random() * bgCanvas.width,
        y: Math.random() * bgCanvas.height,
        vx: (Math.random() - 0.5) * 0.35,
        vy: (Math.random() - 0.5) * 0.35,
        size: Math.random() * 12 + 6,
        type: Math.random() > 0.4 ? "cross" : "hexagon",
        alpha: Math.random() * 0.25 + 0.08
      });
    }

    function animateBg() {
      bgCtx.clearRect(0, 0, bgCanvas.width, bgCanvas.height);

      // Grid
      bgCtx.lineWidth = 1;
      bgCtx.strokeStyle = "rgba(16, 185, 129, 0.04)";
      const sz = 36;
      for (let x = 0; x < bgCanvas.width; x += sz) {
        bgCtx.beginPath(); bgCtx.moveTo(x, 0); bgCtx.lineTo(x, bgCanvas.height); bgCtx.stroke();
      }
      for (let y = 0; y < bgCanvas.height; y += sz) {
        bgCtx.beginPath(); bgCtx.moveTo(0, y); bgCtx.lineTo(bgCanvas.width, y); bgCtx.stroke();
      }

      // Particles
      bgParticles.forEach(p => {
        p.x += p.vx; p.y += p.vy;
        if (p.x < 0) p.x = bgCanvas.width;
        if (p.x > bgCanvas.width) p.x = 0;
        if (p.y < 0) p.y = bgCanvas.height;
        if (p.y > bgCanvas.height) p.y = 0;

        bgCtx.fillStyle = `rgba(16, 185, 129, ${p.alpha})`;
        bgCtx.strokeStyle = `rgba(16, 185, 129, ${p.alpha})`;

        if (p.type === "cross") {
          const s = p.size;
          bgCtx.lineWidth = 1.8;
          bgCtx.beginPath();
          bgCtx.moveTo(p.x - s / 2, p.y); bgCtx.lineTo(p.x + s / 2, p.y);
          bgCtx.moveTo(p.x, p.y - s / 2); bgCtx.lineTo(p.x, p.y + s / 2);
          bgCtx.stroke();
        } else {
          bgCtx.beginPath();
          bgCtx.arc(p.x, p.y, p.size / 3.5, 0, Math.PI * 2);
          bgCtx.fill();
        }
      });

      requestAnimationFrame(animateBg);
    }
    animateBg();

    loadSymptoms();
  </script>
</body>
</html>
"""


# ============================================================================
# HTTP REQUEST HANDLER (REST API + STATIC HTML + CSV EXPORT)
# ============================================================================

class HealthPulseRequestHandler(BaseHTTPRequestHandler):
    """Zero-dependency HTTP Handler for HealthPulse web application and REST API."""

    def log_message(self, format_str, *args):
        """Silently handle routine asset logs; show only critical events."""
        pass

    def send_json(self, status_code, payload):
        """Helper to send JSON response."""
        data = json.dumps(payload).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        """Handle GET requests: serve HTML UI or JSON APIs."""
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        if path in ("/", "/index.html"):
            content = HTML_CONTENT.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(content)))
            self.end_headers()
            self.wfile.write(content)

        elif path == "/api/symptoms":
            records = load_data()
            self.send_json(200, records)

        elif path == "/api/summary":
            records = load_data()
            summary = build_summary(records)
            self.send_json(200, summary)

        elif path == "/api/export/csv":
            records = load_data()
            csv_content = generate_csv(records)
            try:
                with open(CSV_FILE, "w", encoding="utf-8") as f:
                    f.write(csv_content)
            except OSError:
                pass
            data = csv_content.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/csv; charset=utf-8")
            self.send_header("Content-Disposition", "attachment; filename=symptoms.csv")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        """Handle POST requests: add symptom or export report."""
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        if path == "/api/symptoms":
            content_len = int(self.headers.get("Content-Length", 0))
            raw_body = self.rfile.read(content_len).decode("utf-8")
            try:
                payload = json.loads(raw_body)
            except json.JSONDecodeError:
                self.send_json(400, {"error": "Invalid JSON"})
                return

            records = load_data()
            symptom_name = payload.get("symptom", "").strip().lower()
            if not symptom_name:
                self.send_json(400, {"error": "Symptom name is required"})
                return

            severity = int(payload.get("severity", 5))
            severity = max(1, min(10, severity))
            date_str = payload.get("date", "").strip() or datetime.date.today().strftime("%Y-%m-%d")
            notes = payload.get("notes", "").strip()

            new_record = {
                "id": get_next_id(records),
                "date": date_str,
                "symptom": symptom_name,
                "severity": severity,
                "notes": notes
            }
            records.append(new_record)
            save_data(records)
            print(f"[OK] Added symptom ID #{new_record['id']}: {symptom_name} ({severity}/10)")
            self.send_json(201, new_record)

        elif path == "/api/export":
            records = load_data()
            summary = build_summary(records)
            report_text = summary["report_text"]
            try:
                with open(REPORT_FILE, "w", encoding="utf-8") as file:
                    file.write(report_text)
                msg = f"Report successfully exported to '{REPORT_FILE}'."
                print(f"[OK] {msg}")
                self.send_json(200, {"message": msg, "report_text": report_text})
            except OSError as error:
                self.send_json(500, {"error": str(error)})

        else:
            self.send_response(404)
            self.end_headers()

    def do_PUT(self):
        """Handle PUT requests: update existing symptom."""
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        if path == "/api/symptoms":
            content_len = int(self.headers.get("Content-Length", 0))
            raw_body = self.rfile.read(content_len).decode("utf-8")
            try:
                payload = json.loads(raw_body)
            except json.JSONDecodeError:
                self.send_json(400, {"error": "Invalid JSON"})
                return

            target_id = payload.get("id")
            records = load_data()
            found_idx = -1
            for idx, r in enumerate(records):
                if r.get("id") == target_id:
                    found_idx = idx
                    break

            if found_idx == -1:
                self.send_json(404, {"error": f"Record with ID {target_id} not found"})
                return

            current = records[found_idx]
            if "symptom" in payload and payload["symptom"].strip():
                current["symptom"] = payload["symptom"].strip().lower()
            if "severity" in payload:
                current["severity"] = max(1, min(10, int(payload["severity"])))
            if "date" in payload and payload["date"].strip():
                current["date"] = payload["date"].strip()
            if "notes" in payload:
                current["notes"] = payload["notes"].strip()

            save_data(records)
            print(f"[OK] Updated symptom ID #{target_id}")
            self.send_json(200, current)
        else:
            self.send_response(404)
            self.end_headers()

    def do_DELETE(self):
        """Handle DELETE requests: remove symptom by ID."""
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        if path == "/api/symptoms":
            query_params = urllib.parse.parse_qs(parsed.query)
            id_list = query_params.get("id", [])
            if not id_list:
                self.send_json(400, {"error": "Missing 'id' query parameter"})
                return

            try:
                target_id = int(id_list[0])
            except ValueError:
                self.send_json(400, {"error": "Invalid ID format"})
                return

            records = load_data()
            initial_count = len(records)
            records = [r for r in records if r.get("id") != target_id]

            if len(records) == initial_count:
                self.send_json(404, {"error": f"Record ID {target_id} not found"})
                return

            save_data(records)
            print(f"[OK] Deleted symptom ID #{target_id}")
            self.send_json(200, {"success": True, "id": target_id})
        else:
            self.send_response(404)
            self.end_headers()


# ============================================================================
# SERVER STARTUP & BROWSER LAUNCHER
# ============================================================================

def find_free_port(start_port=8000):
    """Find the first available network port starting from start_port."""
    for port in range(start_port, start_port + 20):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(("127.0.0.1", port))
                return port
        except OSError:
            continue
    return start_port


def run_server():
    """Start local HealthPulse HTTP server and automatically open the browser."""
    port = find_free_port(8000)
    server_address = ("127.0.0.1", port)
    httpd = HTTPServer(server_address, HealthPulseRequestHandler)
    url = f"http://127.0.0.1:{port}"

    print("\n" + "=" * 68, flush=True)
    print("   [+] HEALTHPULSE - CYBER-CLINICAL EDITION (BROWSER RUNNING)", flush=True)
    print("=" * 68, flush=True)
    print(f"  * Web Server URL        : {url}", flush=True)
    print(f"  * Persistent Database   : {os.path.abspath(DATA_FILE)}", flush=True)
    print(f"  * Report Export Target  : {os.path.abspath(REPORT_FILE)}", flush=True)
    print("  * Opening your default browser now...", flush=True)
    print("=" * 68, flush=True)
    print("  >> Press Ctrl+C in this terminal at any time to stop the server.\n", flush=True)

    try:
        webbrowser.open(url)
    except Exception as e:
        print(f"Could not open browser automatically ({e}). Please open {url} manually.")

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n[+] HealthPulse server stopped cleanly. Take care and stay healthy!")
        httpd.server_close()


# ============================================================================
# OPTIONAL CONSOLE CLI MODE (RUN WITH: python healthpulse.py --cli)
# ============================================================================

def run_cli():
    """Interactive console menu fallback."""
    records = load_data()
    print("\nHealthPulse - Terminal Mode")
    print(f"Loaded {len(records)} existing record(s) from '{DATA_FILE}'.")

    while True:
        print("\n" + "=" * 65)
        print(r"   [+]  HEALTHPULSE - TERMINAL MENU  [---/\__/\_---]")
        print("=" * 65)
        print("  1. Add New Symptom")
        print("  2. View All Symptoms (Sorted by Date)")
        print("  3. View Health Summary & 7-Day Trend Report")
        print("  4. Export Summary Report to File")
        print("  5. Launch Browser Cyber-Clinical Edition")
        print("  6. Exit")
        print("=" * 65)

        choice = input("Select option (1-6): ").strip()
        if choice == "6":
            print("Goodbye! Stay healthy.")
            break
        elif choice == "5":
            run_server()
            break
        elif choice == "1":
            sym = input("Enter symptom name: ").strip().lower()
            if not sym:
                continue
            try:
                sev = int(input("Enter severity (1-10): ").strip())
            except ValueError:
                sev = 5
            dt = input("Enter date (YYYY-MM-DD) [Default today]: ").strip() or datetime.date.today().strftime("%Y-%m-%d")
            notes = input("Enter notes: ").strip()
            new_r = {"id": get_next_id(records), "date": dt, "symptom": sym, "severity": sev, "notes": notes}
            records.append(new_r)
            save_data(records)
            print(f"[OK] Added ID #{new_r['id']}")
        elif choice == "2":
            print("-" * 75)
            print(f"{'ID':<6} {'Date':<12} {'Symptom':<20} {'Severity':<10} {'Notes'}")
            print("-" * 75)
            for r in sorted(records, key=lambda x: (x.get("date", ""), x.get("id", 0))):
                print(f"{r.get('id'):<6} {r.get('date'):<12} {r.get('symptom', '').capitalize():<20} {r.get('severity')}/10     {r.get('notes', '-')}")
            print("-" * 75)
        elif choice == "3":
            s = build_summary(records)
            print("\n" + s["report_text"])
        elif choice == "4":
            s = build_summary(records)
            with open(REPORT_FILE, "w", encoding="utf-8") as f:
                f.write(s["report_text"])
            print(f"[OK] Report exported to '{REPORT_FILE}'.")


if __name__ == "__main__":
    if "--cli" in sys.argv:
        run_cli()
    else:
        run_server()
