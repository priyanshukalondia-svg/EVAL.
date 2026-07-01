// apps/web/src/app/page.tsx
"use client";

import React, { useState, useEffect, useRef } from "react";
import { 
  Upload, FileText, ArrowRight, User, Play, MessageSquare, 
  BarChart3, Brain, Compass, HelpCircle, Award, CheckCircle2, 
  ChevronRight, Sparkles, RefreshCw, Volume2, Mic, Settings, 
  Database, ShieldAlert, BookOpen, AlertCircle, MicOff, VolumeX
} from "lucide-react";

// API Config
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

// Helper fetch to automatically bypass localtunnel reminder warning screen
const customFetch = (url: string, options: RequestInit = {}) => {
  const headers = {
    ...options.headers,
    "bypass-tunnel-reminder": "true",
  };
  return fetch(url, { ...options, headers });
};

type ViewState = "landing" | "uploading" | "interview" | "report" | "coach" | "admin";

interface UserProfile {
  name: string;
  email: string;
  roleTrack: string;
  companyName: string;
  seniority: string;
}

interface ChatTurn {
  id: string;
  speaker: "ai" | "candidate";
  content: string;
  stage: string;
  created_at: string;
}

interface DimensionScore {
  [key: string]: number;
}

interface StudyItem {
  topic: string;
  resources: string[];
  action_steps: string;
}

interface InterviewReport {
  id: string;
  recommendation: string;
  readiness_score: number;
  dimension_scores: DimensionScore;
  strengths: string[];
  weaknesses: string[];
  knowledge_gaps: string[];
  suggested_improvements: string[];
  study_plan: StudyItem[];
}

interface CoachingFeedback {
  liked: string;
  disliked: string;
  ideal_structure: string;
  better_wording: string;
  rewritten_star: string;
}

export default function Home() {
  // Navigation & States
  const [view, setView] = useState<ViewState>("landing");
  const [profile, setProfile] = useState<UserProfile>({
    name: "",
    email: "",
    roleTrack: "swe",
    companyName: "",
    seniority: "Mid",
  });
  
  // File uploads
  const [resumeFile, setResumeFile] = useState<File | null>(null);
  const [jdText, setJdText] = useState("");
  const [uploadStatus, setUploadStatus] = useState("");
  const [errorMsg, setErrorMsg] = useState("");
  
  // Active interview session
  const [sessionId, setSessionId] = useState("");
  const [chatHistory, setChatHistory] = useState<ChatTurn[]>([]);
  const [candidateAnswer, setCandidateAnswer] = useState("");
  const [isAiThinking, setIsAiThinking] = useState(false);
  const [currentStage, setCurrentStage] = useState("greeting");
  const [currentDifficulty, setCurrentDifficulty] = useState("easy");
  
  // Final Report & Coaching
  const [report, setReport] = useState<InterviewReport | null>(null);
  const [selectedCoachTurn, setSelectedCoachTurn] = useState<string | null>(null);
  const [coachingData, setCoachingData] = useState<CoachingFeedback | null>(null);
  const [loadingCoach, setLoadingCoach] = useState(false);
  
  // Admin stats
  const [adminStats, setAdminStats] = useState<any>(null);

  // Voice Mode & Synthesis States
  const [isVoiceMode, setIsVoiceMode] = useState(false);
  const [aiIsSpeaking, setAiIsSpeaking] = useState(false);
  const [isRecording, setIsRecording] = useState(false);
  const [isTranscribing, setIsTranscribing] = useState(false);
  const [availableVoices, setAvailableVoices] = useState<SpeechSynthesisVoice[]>([]);
  const [selectedVoiceName, setSelectedVoiceName] = useState<string>("");
  
  // Chat scroll anchor
  const chatEndRef = useRef<HTMLDivElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const recognitionRef = useRef<any>(null);
  const answerPrefixRef = useRef("");
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const recordedChunksRef = useRef<Blob[]>([]);
  
  // Audio Web Nodes references
  const audioContextRef = useRef<AudioContext | null>(null);
  const analyserRef = useRef<AnalyserNode | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const visualizerFrameRef = useRef<number | null>(null);

  // Scroll to bottom on chat update
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [chatHistory, isAiThinking]);

  // Load browser voices
  useEffect(() => {
    if (typeof window !== "undefined" && window.speechSynthesis) {
      const loadVoices = () => {
        const voices = window.speechSynthesis.getVoices();
        // Filter English voices
        const engVoices = voices.filter(v => v.lang.startsWith("en"));
        setAvailableVoices(engVoices);
        if (engVoices.length > 0) {
          // Look for Google voices or default to US English
          const defaultVoice = engVoices.find(v => v.name.includes("Google") || v.lang.startsWith("en-US")) || engVoices[0];
          setSelectedVoiceName(defaultVoice.name);
        }
      };
      loadVoices();
      window.speechSynthesis.onvoiceschanged = loadVoices;
    }
  }, []);

  // Initialize Speech Recognition
  useEffect(() => {
    if (typeof window !== "undefined") {
      const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
      if (SpeechRecognition) {
        const rec = new SpeechRecognition();
        rec.continuous = true;
        rec.interimResults = true;
        rec.lang = "en-US";
        
        rec.onresult = (event: any) => {
          let interimTranscript = "";
          let finalTranscript = "";
          
          for (let i = event.resultIndex; i < event.results.length; ++i) {
            const transcript = event.results[i][0].transcript;
            if (event.results[i].isFinal) {
              finalTranscript += transcript;
            } else {
              interimTranscript += transcript;
            }
          }
          
          const prefix = answerPrefixRef.current.trim();
          
          if (finalTranscript) {
            const newFinal = prefix ? `${prefix} ${finalTranscript.trim()}` : finalTranscript.trim();
            answerPrefixRef.current = newFinal;
            setCandidateAnswer(newFinal);
          } else if (interimTranscript) {
            const preview = prefix ? `${prefix} [${interimTranscript.trim()}]` : `[${interimTranscript.trim()}]`;
            setCandidateAnswer(preview);
          }
        };
        
        rec.onerror = (event: any) => {
          console.error("Speech Recognition Error:", event.error);
          if (event.error !== "no-speech") {
            setIsRecording(false);
            stopAudioVisualization();
          }
        };
        
        rec.onend = () => {
          setIsRecording(false);
          stopAudioVisualization();
        };
        
        recognitionRef.current = rec;
      }
    }
  }, []);

  // Browser Text-To-Speech (TTS)
  const speakText = (text: string) => {
    if (typeof window === "undefined" || !window.speechSynthesis) return;
    window.speechSynthesis.cancel(); // Stop current speech
    
    // Clean text of markdown highlights or formatting for speech
    const cleanText = text.replace(/[*_#`\[\]()]/g, "");
    const utterance = new SpeechSynthesisUtterance(cleanText);
    
    const voice = availableVoices.find(v => v.name === selectedVoiceName);
    if (voice) {
      utterance.voice = voice;
    }
    
    utterance.rate = 1.0;
    utterance.pitch = 1.0;
    
    utterance.onstart = () => setAiIsSpeaking(true);
    utterance.onend = () => setAiIsSpeaking(false);
    utterance.onerror = () => setAiIsSpeaking(false);
    
    window.speechSynthesis.speak(utterance);
  };

  // Speech-To-Text Toggle Microphone
  const toggleRecording = () => {
    if (!recognitionRef.current) {
      alert("Real-time Speech Recognition is not supported by your browser. Please use Google Chrome or Microsoft Edge.");
      return;
    }
    
    if (isRecording) {
      recognitionRef.current.stop();
    } else {
      try {
        answerPrefixRef.current = candidateAnswer; // Save current input text
        recognitionRef.current.start();
        setIsRecording(true);
        startAudioVisualization();
      } catch (e) {
        console.error("Failed to start speech recognition:", e);
      }
    }
  };

  // Web Audio Analyser Visualizer & Audio Clip Recorder
  const startAudioVisualization = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      streamRef.current = stream;
      
      // Setup Web Audio Analyser
      const AudioContextClass = window.AudioContext || (window as any).webkitAudioContext;
      const audioContext = new AudioContextClass();
      audioContextRef.current = audioContext;
      
      const source = audioContext.createMediaStreamSource(stream);
      const analyser = audioContext.createAnalyser();
      analyser.fftSize = 64;
      source.connect(analyser);
      analyserRef.current = analyser;
      
      visualizeAudioRealtime();
      
      // Initialize MediaRecorder for high-accuracy Whisper transcription
      const mediaRecorder = new MediaRecorder(stream, { mimeType: 'audio/webm' });
      mediaRecorderRef.current = mediaRecorder;
      recordedChunksRef.current = [];
      
      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          recordedChunksRef.current.push(event.data);
        }
      };
      
      mediaRecorder.onstop = async () => {
        const audioBlob = new Blob(recordedChunksRef.current, { type: 'audio/webm' });
        await uploadAudioForTranscription(audioBlob);
      };
      
      mediaRecorder.start(250); // Capture chunks every 250ms
    } catch (err) {
      console.error("Microphone capture failed:", err);
    }
  };

  // Upload Audio Blob to FastAPI backend for high-accuracy OpenAI Whisper transcription
  const uploadAudioForTranscription = async (blob: Blob) => {
    setIsTranscribing(true);
    setErrorMsg("");
    
    try {
      const formData = new FormData();
      formData.append("file", blob, "recording.webm");
      
      const res = await fetch(`${API_BASE_URL}/api/interviews/transcribe`, {
        method: "POST",
        headers: {
          "bypass-tunnel-reminder": "true"
        },
        body: formData
      });
      
      if (!res.ok) throw new Error("Whisper transcription failed.");
      const data = await res.json();
      
      setCandidateAnswer(prev => {
        // Remove any interim bracketed text and append high-accuracy Whisper transcript
        const cleanedPrev = prev.replace(/\s*\[.*\]\s*$/, "").trim();
        const transcript = data.text.trim();
        
        if (transcript.startsWith("Warning:") || transcript.startsWith("Fallback:")) {
          console.warn(transcript);
          // Strip brackets and keep the browser-native transcribed text
          return prev.replace(/[\[\]]/g, "").trim();
        }
        
        return cleanedPrev ? `${cleanedPrev} ${transcript}` : transcript;
      });
    } catch (err: any) {
      console.error("Transcription upload failed:", err);
      setErrorMsg("Failed to transcribe audio. Please verify your connection or type your answer manually.");
    } finally {
      setIsTranscribing(false);
    }
  };

  const visualizeAudioRealtime = () => {
    if (!canvasRef.current || !analyserRef.current) return;
    const canvas = canvasRef.current;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    
    const analyser = analyserRef.current;
    const bufferLength = analyser.frequencyBinCount;
    const dataArray = new Uint8Array(bufferLength);
    
    const render = () => {
      if (!analyserRef.current) return;
      
      analyser.getByteFrequencyData(dataArray);
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      ctx.strokeStyle = "#ffffff"; // Bright white for active user speech
      ctx.lineWidth = 2.5;
      ctx.beginPath();
      
      const sliceWidth = canvas.width / bufferLength;
      for (let i = 0; i < bufferLength; i++) {
        const x = i * sliceWidth;
        const percent = dataArray[i] / 255.0; // Normalized amplitude
        const offset = percent * (canvas.height / 2) * 1.5;
        const y = (canvas.height / 2) + (i % 2 === 0 ? offset : -offset);
        
        if (i === 0) ctx.moveTo(x, y);
        else ctx.lineTo(x, y);
      }
      ctx.stroke();
      visualizerFrameRef.current = requestAnimationFrame(render);
    };
    
    render();
  };

  const stopAudioVisualization = () => {
    if (visualizerFrameRef.current) {
      cancelAnimationFrame(visualizerFrameRef.current);
      visualizerFrameRef.current = null;
    }
    
    // Stop MediaRecorder if recording is active
    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== "inactive") {
      mediaRecorderRef.current.stop();
    }
    
    if (streamRef.current) {
      streamRef.current.getTracks().forEach(track => track.stop());
      streamRef.current = null;
    }
    if (audioContextRef.current) {
      audioContextRef.current.close();
      audioContextRef.current = null;
    }
    analyserRef.current = null;
  };

  // soundwave breathing visualizer for non-recording states
  useEffect(() => {
    if (view !== "interview" || !canvasRef.current) return;
    const canvas = canvasRef.current;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    
    let animationId: number;
    let phase = 0;
    
    const render = () => {
      // Skip if recording is active, since Web Audio is painting the canvas
      if (isRecording) {
        animationId = requestAnimationFrame(render);
        return;
      }
      
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      ctx.strokeStyle = aiIsSpeaking ? "#22c55e" : "#52525b"; // Green when AI talks, gray when idle
      ctx.lineWidth = 1.5;
      ctx.beginPath();
      
      const sliceWidth = canvas.width / 50;
      for (let i = 0; i < 50; i++) {
        const x = i * sliceWidth;
        const scale = aiIsSpeaking 
          ? Math.sin(i * 0.2 + phase) * 15 * (Math.sin(phase * 1.5) > 0 ? Math.random() * 0.4 + 0.7 : 0.8)
          : Math.sin(i * 0.15 + phase) * 2; // slow pulse breathing when idle
          
        const y = (canvas.height / 2) + scale;
        if (i === 0) ctx.moveTo(x, y);
        else ctx.lineTo(x, y);
      }
      ctx.stroke();
      
      phase += aiIsSpeaking ? 0.2 : 0.03;
      animationId = requestAnimationFrame(render);
    };
    
    render();
    return () => cancelAnimationFrame(animationId);
  }, [view, aiIsSpeaking, isRecording]);

  // Seeding Question Bank Helper on Mount
  useEffect(() => {
    customFetch(`${API_BASE_URL}/api/admin/seed-questions`, { method: "POST" })
      .then(res => res.json())
      .then(data => console.log("Seeding verified:", data))
      .catch(err => console.error("Seeding failed:", err));
  }, []);

  // Handle Form changes
  const handleProfileChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
    setProfile({
      ...profile,
      [e.target.name]: e.target.value
    });
  };

  // Handle file drop/input
  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setResumeFile(e.target.files[0]);
    }
  };

  // Fetch Admin Stats
  const handleFetchAdminStats = async () => {
    setView("admin");
    try {
      const res = await customFetch(`${API_BASE_URL}/api/admin/analytics`);
      const data = await res.json();
      setAdminStats(data);
    } catch (err) {
      console.error(err);
      setErrorMsg("Failed to load admin stats");
    }
  };

  // 1. Initialize Interview Process: Upload Resume -> Parse -> JD Analyze -> Start Session
  const handleStartProcess = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!profile.name || !profile.email || !resumeFile || !jdText || !profile.companyName) {
      setErrorMsg("Please fill out all fields and upload a PDF resume.");
      return;
    }
    
    setView("uploading");
    setErrorMsg("");
    setUploadStatus("Resolving candidate profile & parsing resume...");
    
    try {
      // Step A: Upload Resume
      const resumeFormData = new FormData();
      resumeFormData.append("email", profile.email);
      resumeFormData.append("full_name", profile.name);
      resumeFormData.append("file", resumeFile);
      
      const resumeRes = await customFetch(`${API_BASE_URL}/api/resumes/upload`, {
        method: "POST",
        body: resumeFormData,
      });
      
      if (!resumeRes.ok) throw new Error("Resume parsing failed. Ensure file is PDF or TXT.");
      const resumeData = await resumeRes.json();
      const resumeId = resumeData.id;
      const userId = resumeData.user_id;
      
      // Step B: Analyze JD and Company
      setUploadStatus(`Researching ${profile.companyName} & mapping requirements...`);
      const jdRes = await customFetch(`${API_BASE_URL}/api/job-descriptions/analyze`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          user_id: userId,
          raw_text: jdText,
          company_name: profile.companyName,
          role_title: profile.roleTrack.toUpperCase() + " Role",
          seniority: profile.seniority
        })
      });
      
      if (!jdRes.ok) throw new Error("Job Description analysis failed.");
      const jdData = await jdRes.json();
      const jdId = jdData.id;
      
      // Step C: Initialize Session
      setUploadStatus("Architecting adaptive interview framework...");
      const sessionRes = await customFetch(`${API_BASE_URL}/api/interviews/session`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          user_id: userId,
          resume_id: resumeId,
          jd_id: jdId,
          role_track: profile.roleTrack,
          mode: isVoiceMode ? "voice" : "text"
        })
      });
      
      if (!sessionRes.ok) throw new Error("Failed to start session.");
      const sessionData = await sessionRes.json();
      
      setSessionId(sessionData.id);
      
      // Load Initial history
      const historyRes = await customFetch(`${API_BASE_URL}/api/interviews/session/${sessionData.id}/history`);
      const historyData = await historyRes.json();
      setChatHistory(historyData);
      
      // If voice mode is active, read the greeting aloud
      if (isVoiceMode && historyData.length > 0) {
        // Delay slightly for browser audio loading
        setTimeout(() => speakText(historyData[0].content), 800);
      } else {
        setAiIsSpeaking(true);
        setTimeout(() => setAiIsSpeaking(false), 3000);
      }
      
      setView("interview");
    } catch (err: any) {
      setView("landing");
      setErrorMsg(err.message || "An unexpected error occurred during initialization.");
    }
  };

  // 2. Submit Answer
  const handleSubmitAnswer = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!candidateAnswer.trim() || isAiThinking) return;
    
    // Stop recording if active
    if (isRecording) {
      recognitionRef.current?.stop();
    }
    
    // Add candidate turn locally for instant feedback
    const tempCandidateTurn: ChatTurn = {
      id: "temp",
      speaker: "candidate",
      content: candidateAnswer,
      stage: currentStage,
      created_at: new Date().toISOString()
    };
    
    setChatHistory(prev => [...prev, tempCandidateTurn]);
    const answerSubmitted = candidateAnswer;
    setCandidateAnswer("");
    setIsAiThinking(true);
    
    try {
      const res = await customFetch(`${API_BASE_URL}/api/interviews/session/${sessionId}/answer`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ answer: answerSubmitted })
      });
      
      if (!res.ok) throw new Error("Failed to record answer.");
      const nextTurn = await res.json();
      
      // Reload actual history to ensure UUIDs match
      const historyRes = await customFetch(`${API_BASE_URL}/api/interviews/session/${sessionId}/history`);
      const historyData = await historyRes.json();
      setChatHistory(historyData);
      
      setCurrentStage(nextTurn.stage);
      setCurrentDifficulty(nextTurn.difficulty || "medium");
      
      // Check if session completed
      if (nextTurn.status === "completed") {
        setUploadStatus("Summarizing performance and compiling report...");
        setView("uploading");
        
        // Wait and poll for report
        let attempts = 0;
        const checkReport = setInterval(async () => {
          attempts++;
          try {
            const rRes = await customFetch(`${API_BASE_URL}/api/reports/session/${sessionId}`);
            if (rRes.ok) {
              const rData = await rRes.json();
              setReport(rData);
              clearInterval(checkReport);
              setView("report");
            }
          } catch (e) {
            console.log("Waiting for report compilation...");
          }
          if (attempts > 10) {
            clearInterval(checkReport);
            setView("landing");
            setErrorMsg("Report compilation took too long. Check the admin dashboard.");
          }
        }, 3000);
      } else {
        // AI speaks
        if (isVoiceMode) {
          speakText(nextTurn.content);
        } else {
          setAiIsSpeaking(true);
          setTimeout(() => setAiIsSpeaking(false), 4000);
        }
      }
    } catch (err) {
      console.error(err);
      setErrorMsg("Network error submitting answer.");
    } finally {
      setIsAiThinking(false);
    }
  };

  // 3. Finalize Early
  const handleFinalizeEarly = () => {
    if (!window.confirm("Are you sure you want to end the interview early? We will compile scores based on completed responses.")) return;
    
    // Stop voice activities
    if (typeof window !== "undefined" && window.speechSynthesis) {
      window.speechSynthesis.cancel();
    }
    if (isRecording) {
      recognitionRef.current?.stop();
    }
    
    setView("uploading");
    setUploadStatus("Compiling partial evaluation...");
    
    customFetch(`${API_BASE_URL}/api/interviews/session/${sessionId}/finalize`, { method: "POST" })
      .then(res => {
        if (!res.ok) throw new Error();
        // Wait for report
        setTimeout(async () => {
          const rRes = await customFetch(`${API_BASE_URL}/api/reports/session/${sessionId}`);
          if (rRes.ok) {
            const rData = await rRes.json();
            setReport(rData);
            setView("report");
          } else {
            setView("landing");
            setErrorMsg("Could not load report.");
          }
        }, 5000);
      })
      .catch(err => {
        setView("landing");
        setErrorMsg("Failed to end session.");
      });
  };

  // 4. Fetch Coaching Details for Replay Turn
  const handleSelectCoachTurn = async (turnId: string) => {
    setSelectedCoachTurn(turnId);
    setLoadingCoach(true);
    setCoachingData(null);
    
    try {
      const res = await customFetch(`${API_BASE_URL}/api/reports/turn/${turnId}/coach`);
      if (!res.ok) throw new Error();
      const data = await res.json();
      setCoachingData(data);
    } catch (err) {
      console.error(err);
    } finally {
      setLoadingCoach(false);
    }
  };

  return (
    <div className="flex-1 flex flex-col font-sans">
      {/* Navigation Header */}
      <header className="border-b border-zinc-800 bg-[#0a0a0a]/90 backdrop-blur sticky top-0 z-40 px-6 py-4 flex items-center justify-between">
        <div className="flex items-center space-x-3 cursor-pointer" onClick={() => setView("landing")}>
          <div className="w-8 h-8 rounded-sm bg-neutral-100 flex items-center justify-center text-[#0a0a0a] font-bold text-sm tracking-wider">E.</div>
          <span className="font-semibold text-lg tracking-wider uppercase text-neutral-100">Eval.</span>
        </div>
        <nav className="hidden md:flex items-center space-x-8 text-xs uppercase tracking-widest text-neutral-400 font-medium">
          <button onClick={() => setView("landing")} className={`hover:text-neutral-100 transition-colors ${view === "landing" ? "text-neutral-100 border-b border-neutral-100 pb-1" : ""}`}>Platform.</button>
          {report && (
            <>
              <button onClick={() => setView("report")} className={`hover:text-neutral-100 transition-colors ${view === "report" ? "text-neutral-100 border-b border-neutral-100 pb-1" : ""}`}>Report.</button>
              <button onClick={() => { setView("coach"); if(chatHistory.length > 0) handleSelectCoachTurn(chatHistory.find(t=>t.speaker==='candidate')?.id || "") }} className={`hover:text-neutral-100 transition-colors ${view === "coach" ? "text-neutral-100 border-b border-neutral-100 pb-1" : ""}`}>Coach.</button>
            </>
          )}
          <button onClick={handleFetchAdminStats} className={`hover:text-neutral-100 transition-colors ${view === "admin" ? "text-neutral-100 border-b border-neutral-100 pb-1" : ""}`}>Admin.</button>
        </nav>
        <div className="flex items-center space-x-4">
          <div className="px-3 py-1 border border-zinc-800 text-[10px] text-zinc-400 uppercase tracking-widest rounded-full flex items-center space-x-1.5">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse"></span>
            <span>Local Cluster</span>
          </div>
        </div>
      </header>

      {/* Main Container */}
      <main className="flex-1 flex flex-col justify-center max-w-7xl w-full mx-auto p-4 md:p-8">
        
        {/* VIEW 1: LANDING & UPLOAD */}
        {view === "landing" && (
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 py-4">
            
            {/* Left Column: Intro */}
            <div className="lg:col-span-5 flex flex-col justify-center space-y-6">
              <h1 className="text-4xl md:text-5xl font-bold tracking-tight text-neutral-100 leading-none">
                RECRUITMENT.<br/>
                EVALUATION.<br/>
                INTELLIGENCE.
              </h1>
              <p className="text-sm text-neutral-400 leading-relaxed font-light">
                An advanced AI recruitment platform conducting technical and behavioral interviews indistinguishable from leading organizations. Evaluates real-time performance against granular hiring rubrics with career-coach critiques.
              </p>
              
              <div className="border border-zinc-800 p-4 rounded bg-zinc-900/10 space-y-3">
                <h3 className="text-xs font-semibold tracking-wider uppercase text-neutral-300 flex items-center space-x-2">
                  <Sparkles className="w-3.5 h-3.5 text-zinc-400" />
                  <span>Platform Engine Features.</span>
                </h3>
                <ul className="text-xs text-neutral-400 space-y-2 font-light">
                  <li className="flex items-start space-x-2">
                    <span className="text-emerald-500 mr-1">✓</span>
                    <span>Interactive Voice mode: AI speaks questions and transcribes your microphone.</span>
                  </li>
                  <li className="flex items-start space-x-2">
                    <span className="text-emerald-500 mr-1">✓</span>
                    <span>Adaptive question reasoning, matching your CV bullets.</span>
                  </li>
                  <li className="flex items-start space-x-2">
                    <span className="text-emerald-500 mr-1">✓</span>
                    <span>Detailed feedback with complete rewritten STAR answers.</span>
                  </li>
                </ul>
              </div>
            </div>

            {/* Right Column: Setup Form */}
            <div className="lg:col-span-7 border border-zinc-800 p-6 md:p-8 bg-zinc-950/40 rounded flex flex-col justify-between">
              <h2 className="text-lg font-medium tracking-wide uppercase mb-6 pb-2 border-b border-zinc-800 text-neutral-200">
                Setup Interview.
              </h2>
              
              {errorMsg && (
                <div className="mb-6 p-4 border border-red-900/50 bg-red-950/20 text-red-400 text-xs rounded flex items-start space-x-2">
                  <AlertCircle className="w-4 h-4 mt-0.5 flex-shrink-0" />
                  <span>{errorMsg}</span>
                </div>
              )}

              <form onSubmit={handleStartProcess} className="space-y-6">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="space-y-1.5">
                    <label className="text-[10px] uppercase tracking-widest text-neutral-400 font-medium">Candidate Name</label>
                    <input 
                      type="text" required name="name" value={profile.name} onChange={handleProfileChange}
                      placeholder="Jane Doe" 
                      className="w-full bg-zinc-900/60 border border-zinc-800 rounded px-3.5 py-2 text-sm focus:outline-none focus:border-neutral-200 transition-colors"
                    />
                  </div>
                  <div className="space-y-1.5">
                    <label className="text-[10px] uppercase tracking-widest text-neutral-400 font-medium">Email Address</label>
                    <input 
                      type="email" required name="email" value={profile.email} onChange={handleProfileChange}
                      placeholder="jane@example.com" 
                      className="w-full bg-zinc-900/60 border border-zinc-800 rounded px-3.5 py-2 text-sm focus:outline-none focus:border-neutral-200 transition-colors"
                    />
                  </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  <div className="space-y-1.5">
                    <label className="text-[10px] uppercase tracking-widest text-neutral-400 font-medium">Role Track</label>
                    <select 
                      name="roleTrack" value={profile.roleTrack} onChange={handleProfileChange}
                      className="w-full bg-zinc-900/60 border border-zinc-800 rounded px-3.5 py-2 text-sm focus:outline-none focus:border-neutral-200 transition-colors text-neutral-300"
                    >
                      <option value="swe">Software Engineer</option>
                      <option value="backend_developer">Backend Developer</option>
                      <option value="data_analyst">Data Analyst</option>
                      <option value="product_manager">Product Manager</option>
                      <option value="ui_ux_designer">UI/UX Designer</option>
                    </select>
                  </div>
                  <div className="space-y-1.5">
                    <label className="text-[10px] uppercase tracking-widest text-neutral-400 font-medium">Target Company</label>
                    <input 
                      type="text" required name="companyName" value={profile.companyName} onChange={handleProfileChange}
                      placeholder="Google" 
                      className="w-full bg-zinc-900/60 border border-zinc-800 rounded px-3.5 py-2 text-sm focus:outline-none focus:border-neutral-200 transition-colors"
                    />
                  </div>
                  <div className="space-y-1.5">
                    <label className="text-[10px] uppercase tracking-widest text-neutral-400 font-medium">Seniority</label>
                    <select 
                      name="seniority" value={profile.seniority} onChange={handleProfileChange}
                      className="w-full bg-zinc-900/60 border border-zinc-800 rounded px-3.5 py-2 text-sm focus:outline-none focus:border-neutral-200 transition-colors text-neutral-300"
                    >
                      <option value="Junior">Junior</option>
                      <option value="Mid">Mid</option>
                      <option value="Senior">Senior</option>
                    </select>
                  </div>
                </div>

                {/* Voice Mode Selector Card */}
                <div className="border border-zinc-850 p-4 rounded bg-zinc-900/10 flex items-center justify-between">
                  <div className="space-y-0.5">
                    <h4 className="text-xs font-semibold text-neutral-200 uppercase tracking-wider flex items-center space-x-1.5">
                      <Volume2 className="w-3.5 h-3.5 text-zinc-400" />
                      <span>Interactive Voice Mode.</span>
                    </h4>
                    <p className="text-[10px] text-zinc-500 font-light">
                      AI Recruiter speaks the question and transcribes your microphone.
                    </p>
                  </div>
                  <button
                    type="button"
                    onClick={() => setIsVoiceMode(!isVoiceMode)}
                    className={`relative inline-flex h-5 w-10 flex-shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none ${
                      isVoiceMode ? "bg-neutral-100" : "bg-zinc-800"
                    }`}
                  >
                    <span
                      className={`pointer-events-none inline-block h-4 w-4 transform rounded-full shadow ring-0 transition duration-200 ease-in-out ${
                        isVoiceMode ? "translate-x-5 bg-zinc-950" : "translate-x-0 bg-neutral-400"
                      }`}
                    />
                  </button>
                </div>

                <div className="space-y-4 pt-2">
                  <div className="border border-dashed border-zinc-800 p-6 rounded bg-zinc-900/5 hover:bg-zinc-900/20 transition-colors flex flex-col items-center justify-center space-y-2 cursor-pointer relative">
                    <input 
                      type="file" accept=".pdf,.txt" onChange={handleFileChange} required
                      className="absolute inset-0 opacity-0 cursor-pointer"
                    />
                    <Upload className="w-6 h-6 text-zinc-500" />
                    <span className="text-xs text-neutral-300 font-medium">
                      {resumeFile ? resumeFile.name : "Upload PDF or TXT Resume"}
                    </span>
                    <span className="text-[10px] text-zinc-500">Max size 5MB</span>
                  </div>

                  <div className="space-y-1.5">
                    <label className="text-[10px] uppercase tracking-widest text-neutral-400 font-medium">Job Description Text</label>
                    <textarea 
                      required value={jdText} onChange={(e) => setJdText(e.target.value)}
                      placeholder="Paste the job description or role requirements here..."
                      className="w-full h-32 bg-zinc-900/60 border border-zinc-800 rounded px-3.5 py-2.5 text-sm focus:outline-none focus:border-neutral-200 transition-colors resize-none font-light"
                    />
                  </div>
                </div>

                <button 
                  type="submit" 
                  className="w-full bg-neutral-100 text-[#0a0a0a] hover:bg-neutral-200 font-semibold py-3 px-4 rounded text-xs uppercase tracking-widest flex items-center justify-center space-x-2 transition-all"
                >
                  <span>Initialize Interview Engine</span>
                  <ArrowRight className="w-3.5 h-3.5" />
                </button>
              </form>
            </div>
          </div>
        )}

        {/* VIEW 2: LOADING / UPLOADING STATS */}
        {view === "uploading" && (
          <div className="flex-1 flex flex-col items-center justify-center py-20 space-y-8">
            <div className="relative">
              {/* Outer pulsing ring */}
              <div className="w-16 h-16 rounded-full border border-neutral-700 animate-ping absolute inset-0 opacity-25"></div>
              {/* Inner rotating wheel */}
              <div className="w-16 h-16 rounded-full border border-neutral-400 border-t-transparent animate-spin"></div>
            </div>
            <div className="space-y-2 text-center max-w-sm">
              <h3 className="text-sm font-semibold tracking-wider uppercase text-neutral-300">Evaluating Schema.</h3>
              <p className="text-xs text-neutral-500 font-light leading-relaxed">{uploadStatus}</p>
            </div>
          </div>
        )}

        {/* VIEW 3: INTERVIEW ROOM */}
        {view === "interview" && (
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 py-4 flex-1">
            
            {/* Left Side: Mock Video & Stats (5 cols) */}
            <div className="lg:col-span-5 flex flex-col space-y-6">
              
              {/* Webcam Placeholder Grid */}
              <div className="grid grid-cols-2 gap-4">
                {/* Candidate Feed */}
                <div className={`border rounded aspect-[4/3] flex flex-col justify-between p-4 relative overflow-hidden group transition-all ${
                  isRecording ? "border-white bg-zinc-900/40" : "border-zinc-800 bg-zinc-950"
                }`}>
                  <div className="absolute inset-0 bg-radial-gradient from-zinc-900 to-zinc-950 opacity-50 z-0"></div>
                  <div className="px-2 py-0.5 border border-zinc-800 text-[8px] tracking-widest uppercase text-zinc-400 rounded-full w-fit bg-zinc-900/60 z-10">Candidate</div>
                  <div className="flex-1 flex items-center justify-center z-10">
                    <div className={`w-12 h-12 rounded-full border bg-zinc-900 flex items-center justify-center text-neutral-300 relative transition-all ${
                      isRecording ? "border-white" : "border-zinc-800"
                    }`}>
                      <User className="w-6 h-6" />
                      {isRecording && (
                        <span className="absolute -inset-1 rounded-full border border-white animate-ping opacity-40"></span>
                      )}
                    </div>
                  </div>
                  <div className="flex items-center justify-between text-[10px] text-zinc-500 z-10">
                    <span>{profile.name} (You)</span>
                    <span className={`w-2 h-2 rounded-full ${isRecording ? "bg-white animate-pulse" : "bg-red-500 animate-pulse"}`}></span>
                  </div>
                </div>

                {/* AI Recruiter Feed */}
                <div className={`border rounded aspect-[4/3] flex flex-col justify-between p-4 relative overflow-hidden group transition-all ${
                  aiIsSpeaking ? "border-emerald-500" : "border-zinc-800 bg-zinc-950"
                }`}>
                  <div className="absolute inset-0 bg-gradient-to-b from-zinc-900 to-zinc-950 z-0"></div>
                  <div className="px-2 py-0.5 border border-zinc-800 text-[8px] tracking-widest uppercase text-zinc-400 rounded-full w-fit bg-zinc-900/60 z-10">AI Recruiter</div>
                  <div className="flex-1 flex items-center justify-center z-10">
                    <div className={`w-12 h-12 rounded-full border ${aiIsSpeaking ? 'border-emerald-500 bg-emerald-950/20' : 'border-zinc-800 bg-zinc-900'} flex items-center justify-center text-neutral-300 relative transition-all`}>
                      <Brain className={`w-6 h-6 ${aiIsSpeaking ? 'text-emerald-400' : 'text-zinc-400'}`} />
                      {aiIsSpeaking && (
                        <span className="absolute -inset-1 rounded-full border border-emerald-500 animate-ping opacity-30"></span>
                      )}
                    </div>
                  </div>
                  <div className="flex items-center justify-between text-[10px] text-zinc-500 z-10">
                    <span>Hiring Committee</span>
                    <div className="flex items-center space-x-1">
                      <Volume2 className={`w-3.5 h-3.5 ${aiIsSpeaking ? 'text-emerald-500' : 'text-zinc-500'}`} />
                      <span>{aiIsSpeaking ? "Speaking" : "Muted"}</span>
                    </div>
                  </div>
                </div>
              </div>

              {/* Status metrics card */}
              <div className="border border-zinc-800 rounded p-5 bg-zinc-950/20 space-y-4">
                <div className="flex items-center justify-between border-b border-zinc-900 pb-2">
                  <h3 className="text-xs font-semibold tracking-wider uppercase text-neutral-300">
                    Session Parameters.
                  </h3>
                  <div className="flex items-center space-x-1 border border-zinc-800 rounded px-2 py-0.5 bg-zinc-900/50">
                    <Volume2 className="w-3 h-3 text-zinc-500" />
                    <span className="text-[8px] uppercase tracking-widest font-mono text-zinc-400">{isVoiceMode ? "Voice mode Active" : "Text Mode"}</span>
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-4 text-xs font-light">
                  <div className="space-y-1">
                    <span className="text-zinc-500 block text-[9px] uppercase tracking-wider">Role Track</span>
                    <span className="text-neutral-300 uppercase font-mono">{profile.roleTrack}</span>
                  </div>
                  <div className="space-y-1">
                    <span className="text-zinc-500 block text-[9px] uppercase tracking-wider">Target Domain</span>
                    <span className="text-neutral-300 uppercase font-mono">{profile.companyName}</span>
                  </div>
                  <div className="space-y-1">
                    <span className="text-zinc-500 block text-[9px] uppercase tracking-wider">Active Stage</span>
                    <span className="text-neutral-300 uppercase font-mono">{currentStage.replace("_", " ")}</span>
                  </div>
                  <div className="space-y-1">
                    <span className="text-zinc-500 block text-[9px] uppercase tracking-wider">Difficulty Level</span>
                    <span className="text-neutral-300 uppercase font-mono">{currentDifficulty}</span>
                  </div>
                </div>
                
                {/* Voice Selection Settings Panel (Only in voice mode) */}
                {isVoiceMode && availableVoices.length > 0 && (
                  <div className="pt-3 border-t border-zinc-900 space-y-1.5 text-xs">
                    <label className="text-[9px] uppercase tracking-wider text-zinc-500 font-medium">AI Recruiter Voice</label>
                    <select
                      value={selectedVoiceName}
                      onChange={(e) => setSelectedVoiceName(e.target.value)}
                      className="w-full bg-zinc-900 border border-zinc-800 rounded px-2.5 py-1.5 text-[11px] focus:outline-none focus:border-neutral-200 transition-colors text-neutral-300"
                    >
                      {availableVoices.map(v => (
                        <option key={v.name} value={v.name}>{v.name} ({v.lang})</option>
                      ))}
                    </select>
                  </div>
                )}
                
                {/* Audio soundwave rendering container */}
                <div className="pt-2 flex flex-col items-center justify-center border-t border-zinc-900">
                  <span className="text-[8px] uppercase tracking-widest text-zinc-500 mb-1">
                    {isRecording ? "Live Vocal Amplitude" : "Conversational Latency"}
                  </span>
                  <canvas ref={canvasRef} width={280} height={50} className="w-full h-10 border border-zinc-900 rounded bg-zinc-950/40" />
                </div>
              </div>

              <button 
                onClick={handleFinalizeEarly}
                className="w-full border border-red-900/50 hover:bg-red-950/20 text-red-400 py-3 rounded text-[10px] uppercase tracking-widest font-semibold transition-all"
              >
                Terminate & Finalize Session
              </button>
            </div>

            {/* Right Side: Chat Transcript & Feed (7 cols) */}
            <div className="lg:col-span-7 border border-zinc-800 rounded bg-zinc-950/20 flex flex-col h-[600px] justify-between overflow-hidden">
              
              {/* Chat Log Header */}
              <div className="border-b border-zinc-800 px-5 py-3.5 flex items-center justify-between bg-[#0a0a0a]/50">
                <span className="text-xs uppercase tracking-widest text-neutral-300 font-semibold">Live Transcript.</span>
                <span className="text-[10px] font-mono text-zinc-500">Stage: {chatHistory.length} turns</span>
              </div>

              {/* Conversational content container */}
              <div className="flex-1 p-5 overflow-y-auto space-y-4 scrollbar-thin">
                {chatHistory.map((turn, idx) => (
                  <div 
                    key={turn.id + idx} 
                    className={`flex flex-col max-w-[85%] ${turn.speaker === "ai" ? "self-start mr-auto" : "self-end ml-auto"}`}
                  >
                    <div className="flex items-center space-x-1.5 mb-1">
                      <span className={`text-[9px] uppercase tracking-wider font-semibold ${turn.speaker === "ai" ? "text-neutral-400" : "text-zinc-500"}`}>
                        {turn.speaker === "ai" ? "AI Recruiter." : "Candidate (You)."}
                      </span>
                      {turn.speaker === "ai" && (
                        <span className="px-1 border border-zinc-800 text-[7px] text-zinc-500 uppercase tracking-widest rounded-sm bg-zinc-900">
                          {turn.stage.replace("_", " ")}
                        </span>
                      )}
                    </div>
                    <div className={`p-3.5 rounded text-xs leading-relaxed font-light ${
                      turn.speaker === "ai" 
                        ? "bg-zinc-900/60 border border-zinc-800 text-neutral-200" 
                        : "bg-neutral-100 text-[#0a0a0a] border border-neutral-200 font-normal"
                    }`}>
                      {turn.content}
                    </div>
                  </div>
                ))}
                
                {isAiThinking && (
                  <div className="flex flex-col self-start mr-auto max-w-[85%]">
                    <span className="text-[9px] uppercase tracking-wider text-zinc-500 mb-1 font-semibold">AI Recruiter.</span>
                    <div className="p-3.5 rounded bg-zinc-900/60 border border-zinc-800 text-neutral-400 text-xs flex items-center space-x-2">
                      <div className="flex space-x-1">
                        <div className="w-1.5 h-1.5 bg-neutral-400 rounded-full animate-bounce" style={{ animationDelay: "0ms" }}></div>
                        <div className="w-1.5 h-1.5 bg-neutral-400 rounded-full animate-bounce" style={{ animationDelay: "150ms" }}></div>
                        <div className="w-1.5 h-1.5 bg-neutral-400 rounded-full animate-bounce" style={{ animationDelay: "300ms" }}></div>
                      </div>
                      <span className="text-[10px] tracking-wider uppercase font-light">Analyzing response context...</span>
                    </div>
                  </div>
                )}
                
                <div ref={chatEndRef} />
              </div>

              {/* Chat Input form */}
              <form onSubmit={handleSubmitAnswer} className="p-4 border-t border-zinc-800 bg-[#0a0a0a]/50 flex items-center space-x-3">
                
                {/* Voice microphone Toggle button */}
                {isVoiceMode && (
                  <button
                    type="button"
                    onClick={toggleRecording}
                    className={`p-3 rounded-full border transition-all ${
                      isRecording 
                        ? "bg-white border-white text-zinc-950 animate-pulse" 
                        : "bg-zinc-900 border-zinc-800 text-neutral-400 hover:text-neutral-100 hover:border-zinc-700"
                    }`}
                    title={isRecording ? "Stop Recording" : "Record Answer"}
                  >
                    {isRecording ? <MicOff className="w-4 h-4" /> : <Mic className="w-4 h-4" />}
                  </button>
                )}

                <input 
                  type="text" required value={candidateAnswer} onChange={(e) => setCandidateAnswer(e.target.value)}
                  disabled={isAiThinking || isTranscribing}
                  placeholder={
                    isAiThinking 
                      ? "Recruiter is analyzing response..." 
                      : isTranscribing
                      ? "OpenAI Whisper is transcribing your audio... please wait."
                      : isRecording 
                      ? "Recording vocal audio... Click microphone again to transcribe." 
                      : "Type your response or click mic to speak..."
                  }
                  className="flex-1 bg-zinc-900/80 border border-zinc-800 rounded px-4 py-3 text-xs focus:outline-none focus:border-neutral-200 transition-colors text-neutral-200 disabled:opacity-55 font-light"
                />
                <button 
                  type="submit" 
                  disabled={!candidateAnswer.trim() || isAiThinking || isTranscribing}
                  className="bg-neutral-100 text-[#0a0a0a] hover:bg-neutral-200 disabled:opacity-40 px-5 py-3 rounded text-[10px] uppercase tracking-widest font-semibold flex items-center space-x-1.5 transition-colors cursor-pointer"
                >
                  <span>Submit</span>
                  <ChevronRight className="w-3.5 h-3.5" />
                </button>
              </form>
            </div>
          </div>
        )}

        {/* VIEW 4: EXECUTIVE REPORT VIEW */}
        {view === "report" && report && (
          <div className="space-y-8 py-4">
            
            {/* Header recommendation banner */}
            <div className="border border-zinc-800 rounded p-6 bg-zinc-950/40 grid grid-cols-1 md:grid-cols-12 gap-6 items-center">
              <div className="md:col-span-8 space-y-2">
                <div className="flex items-center space-x-2 text-[10px] tracking-widest text-zinc-500 uppercase">
                  <span>Hiring Evaluation</span>
                  <span>•</span>
                  <span>Session Summary</span>
                </div>
                <h2 className="text-3xl font-bold tracking-tight text-neutral-100">
                  EXECUTIVE.REPORT
                </h2>
                <p className="text-xs text-neutral-400 font-light">
                  A synthesis of overall competencies, strengths, weaknesses, gaps, and STAR structured answer metrics.
                </p>
              </div>

              <div className="md:col-span-4 flex flex-col md:items-end space-y-2">
                <div className="text-[10px] text-zinc-500 uppercase tracking-widest">Recommendation</div>
                <span className={`px-4 py-1.5 rounded-full text-xs font-semibold tracking-widest uppercase w-fit ${
                  report.recommendation.includes("strong_hire") || report.recommendation === "hire"
                    ? "bg-emerald-950/30 text-emerald-400 border border-emerald-900/50"
                    : report.recommendation.includes("no_hire")
                    ? "bg-red-950/30 text-red-400 border border-red-900/50"
                    : "bg-yellow-950/30 text-yellow-400 border border-yellow-900/50"
                }`}>
                  {report.recommendation.replace("_", " ")}
                </span>
              </div>
            </div>

            {/* Score grids */}
            <div className="grid grid-cols-1 md:grid-cols-12 gap-6">
              
              {/* Overall readiness card (4 cols) */}
              <div className="md:col-span-4 border border-zinc-800 p-6 rounded bg-zinc-950/20 flex flex-col items-center justify-center space-y-4">
                <span className="text-[10px] text-zinc-500 uppercase tracking-widest font-semibold">Readiness Index.</span>
                <div className="relative w-36 h-36 flex items-center justify-center border-4 border-zinc-900 rounded-full">
                  <div className="absolute inset-2 rounded-full border border-dashed border-zinc-800"></div>
                  <span className="text-4xl font-bold font-mono text-neutral-100">{Math.round(report.readiness_score)}%</span>
                </div>
                <p className="text-[10px] text-zinc-500 font-light text-center">
                  Synthesized rating based on comparative mapping with role expectations.
                </p>
              </div>

              {/* Dimension sliders card (8 cols) */}
              <div className="md:col-span-8 border border-zinc-800 p-6 rounded bg-zinc-950/20 space-y-4">
                <h3 className="text-xs font-semibold tracking-wider uppercase text-neutral-300 pb-2 border-b border-zinc-900">
                  Rubric Dimension Ratings.
                </h3>
                <div className="space-y-4">
                  {Object.entries(report.dimension_scores).map(([dim, val]) => (
                    <div key={dim} className="space-y-1.5">
                      <div className="flex items-center justify-between text-xs font-light">
                        <span className="text-neutral-400 uppercase font-mono">{dim.replace("_", " ")}</span>
                        <span className="text-neutral-300 font-semibold">{Math.round(val)}/100</span>
                      </div>
                      <div className="w-full bg-zinc-900 rounded-full h-1.5 overflow-hidden">
                        <div className="bg-neutral-200 h-1.5 rounded-full" style={{ width: `${val}%` }}></div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

            </div>

            {/* Strengths / Weaknesses */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              
              {/* Strengths */}
              <div className="border border-zinc-800 p-6 rounded bg-zinc-950/20 space-y-4">
                <h3 className="text-xs font-semibold tracking-wider uppercase text-emerald-400 pb-2 border-b border-zinc-900 flex items-center space-x-2">
                  <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                  <span>Key Strengths.</span>
                </h3>
                <ul className="space-y-3">
                  {report.strengths.map((str, idx) => (
                    <li key={idx} className="text-xs text-neutral-400 leading-relaxed font-light flex items-start space-x-2.5">
                      <span className="text-emerald-500 mt-0.5">•</span>
                      <span>{str}</span>
                    </li>
                  ))}
                </ul>
              </div>

              {/* Weaknesses / Gaps */}
              <div className="border border-zinc-800 p-6 rounded bg-zinc-950/20 space-y-4">
                <h3 className="text-xs font-semibold tracking-wider uppercase text-red-400 pb-2 border-b border-zinc-900 flex items-center space-x-2">
                  <ShieldAlert className="w-4 h-4 text-red-400" />
                  <span>Focus Gaps.</span>
                </h3>
                <ul className="space-y-3">
                  {report.weaknesses.map((weak, idx) => (
                    <li key={idx} className="text-xs text-neutral-400 leading-relaxed font-light flex items-start space-x-2.5">
                      <span className="text-red-500 mt-0.5">•</span>
                      <span>{weak}</span>
                    </li>
                  ))}
                </ul>
              </div>

            </div>

            {/* Suggested curriculum / Study plan */}
            <div className="border border-zinc-800 p-6 rounded bg-zinc-950/20 space-y-5">
              <h3 className="text-xs font-semibold tracking-wider uppercase text-neutral-300 pb-2 border-b border-zinc-900 flex items-center space-x-2">
                <BookOpen className="w-4 h-4 text-zinc-400" />
                <span>Recommended Study Plan.</span>
              </h3>
              
              <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                {report.study_plan.map((item, idx) => (
                  <div key={idx} className="border border-zinc-900 p-4 rounded bg-[#0d0d0d]/60 space-y-3 flex flex-col justify-between">
                    <div className="space-y-1.5">
                      <span className="text-[10px] text-zinc-500 uppercase tracking-widest font-mono">Topic {idx+1}</span>
                      <h4 className="text-xs font-semibold text-neutral-200">{item.topic}</h4>
                      <p className="text-[11px] text-neutral-400 font-light leading-relaxed">{item.action_steps}</p>
                    </div>
                    <div className="pt-2 border-t border-zinc-900 space-y-1">
                      <span className="text-[9px] uppercase tracking-wider text-zinc-500 block">Study Materials</span>
                      <div className="flex flex-wrap gap-1">
                        {item.resources.map((res, rIdx) => (
                          <span key={rIdx} className="px-1.5 py-0.5 border border-zinc-800 text-[8px] text-zinc-400 bg-zinc-900 rounded font-light">{res}</span>
                        ))}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Navigation options */}
            <div className="flex items-center justify-center space-x-4">
              <button 
                onClick={() => { setView("coach"); if(chatHistory.length > 0) handleSelectCoachTurn(chatHistory.find(t=>t.speaker==='candidate')?.id || "") }}
                className="bg-neutral-100 text-[#0a0a0a] hover:bg-neutral-200 font-semibold py-3 px-6 rounded text-xs uppercase tracking-widest flex items-center space-x-2 transition-colors cursor-pointer"
              >
                <span>Enter AI Coach Room</span>
                <Compass className="w-3.5 h-3.5" />
              </button>
              <button 
                onClick={() => setView("landing")}
                className="border border-zinc-800 text-neutral-300 hover:bg-zinc-900 font-semibold py-3 px-6 rounded text-xs uppercase tracking-widest flex items-center space-x-2 transition-colors cursor-pointer"
              >
                <span>New Interview</span>
                <RefreshCw className="w-3.5 h-3.5" />
              </button>
            </div>

          </div>
        )}

        {/* VIEW 5: COACH MODE */}
        {view === "coach" && (
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 py-4 flex-1">
            
            {/* Left Side: Conversation log (5 cols) */}
            <div className="lg:col-span-5 border border-zinc-800 rounded bg-zinc-950/20 flex flex-col h-[580px] overflow-hidden">
              <div className="border-b border-zinc-800 px-5 py-3.5 bg-[#0a0a0a]/50">
                <span className="text-xs uppercase tracking-widest text-neutral-300 font-semibold">Select Answer to Coach.</span>
              </div>
              <div className="flex-1 p-4 overflow-y-auto space-y-3.5 scrollbar-thin">
                {chatHistory.filter(t => t.speaker === "candidate").map((turn, idx) => (
                  <button
                    key={turn.id + idx}
                    onClick={() => handleSelectCoachTurn(turn.id)}
                    className={`w-full text-left p-3.5 border rounded transition-all flex flex-col space-y-2 cursor-pointer ${
                      selectedCoachTurn === turn.id
                        ? "bg-zinc-900 border-neutral-300"
                        : "bg-zinc-950/40 border-zinc-800 hover:border-zinc-700"
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      <span className="text-[10px] text-zinc-500 uppercase tracking-widest font-mono">Response {idx+1}</span>
                      <span className="px-1 border border-zinc-800 text-[8px] text-zinc-500 uppercase tracking-widest rounded bg-zinc-900">
                        {turn.stage.replace("_", " ")}
                      </span>
                    </div>
                    <p className="text-xs text-neutral-300 line-clamp-2 leading-relaxed font-light italic">
                      "{turn.content}"
                    </p>
                  </button>
                ))}
              </div>
            </div>

            {/* Right Side: Coach critique details (7 cols) */}
            <div className="lg:col-span-7 border border-zinc-800 rounded bg-zinc-950/20 flex flex-col h-[580px] overflow-hidden">
              
              <div className="border-b border-zinc-800 px-5 py-3.5 flex items-center justify-between bg-[#0a0a0a]/50">
                <span className="text-xs uppercase tracking-widest text-neutral-300 font-semibold">Career Coach Analysis.</span>
                <span className="text-[9px] uppercase tracking-widest text-zinc-400 bg-neutral-900 border border-zinc-800 px-2 py-0.5 rounded">STAR Method Evaluator</span>
              </div>

              <div className="flex-1 p-6 overflow-y-auto space-y-6 scrollbar-thin">
                {loadingCoach ? (
                  <div className="h-full flex flex-col items-center justify-center space-y-3">
                    <RefreshCw className="w-6 h-6 text-zinc-400 animate-spin" />
                    <span className="text-xs uppercase tracking-widest text-zinc-500 font-light">Analyzing response structure...</span>
                  </div>
                ) : coachingData ? (
                  <div className="space-y-6">
                    
                    {/* Recruiter Reaction */}
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      {/* Liked */}
                      <div className="border border-zinc-900 p-4 rounded bg-zinc-900/10 space-y-2">
                        <h4 className="text-[10px] uppercase tracking-widest font-semibold text-emerald-400 flex items-center space-x-1.5">
                          <CheckCircle2 className="w-3.5 h-3.5" />
                          <span>What Recruiter Liked.</span>
                        </h4>
                        <p className="text-[11px] text-neutral-400 leading-relaxed font-light">{coachingData.liked}</p>
                      </div>
                      {/* Disliked */}
                      <div className="border border-zinc-900 p-4 rounded bg-zinc-900/10 space-y-2">
                        <h4 className="text-[10px] uppercase tracking-widest font-semibold text-red-400 flex items-center space-x-1.5">
                          <ShieldAlert className="w-3.5 h-3.5" />
                          <span>What Was Weak.</span>
                        </h4>
                        <p className="text-[11px] text-neutral-400 leading-relaxed font-light">{coachingData.disliked}</p>
                      </div>
                    </div>

                    {/* Ideal Structure */}
                    <div className="space-y-2">
                      <h4 className="text-[10px] uppercase tracking-widest font-semibold text-zinc-300 block">Recommended Architecture.</h4>
                      <p className="text-xs text-neutral-400 leading-relaxed font-light p-3.5 border border-zinc-900 bg-zinc-950/60 rounded">
                        {coachingData.ideal_structure}
                      </p>
                    </div>

                    {/* Wording modifications */}
                    <div className="space-y-2">
                      <h4 className="text-[10px] uppercase tracking-widest font-semibold text-zinc-300 block">Wording Upgrades.</h4>
                      <p className="text-xs text-neutral-400 leading-relaxed font-light p-3.5 border border-zinc-900 bg-zinc-950/60 rounded">
                        {coachingData.better_wording}
                      </p>
                    </div>

                    {/* Rewrite STAR answer */}
                    <div className="space-y-2.5 pt-2">
                      <h4 className="text-[10px] uppercase tracking-widest font-semibold text-neutral-200 flex items-center space-x-2">
                        <Sparkles className="w-3.5 h-3.5 text-zinc-300" />
                        <span>Ideal STAR Framework Rewrite.</span>
                      </h4>
                      <div className="p-4 border border-neutral-800 bg-[#0c0c0c] rounded text-xs leading-relaxed text-neutral-200 font-light border-l-4 border-l-neutral-200">
                        {coachingData.rewritten_star}
                      </div>
                    </div>

                  </div>
                ) : (
                  <div className="h-full flex flex-col items-center justify-center text-center space-y-2 text-zinc-500 font-light">
                    <HelpCircle className="w-8 h-8 text-zinc-600" />
                    <p className="text-xs uppercase tracking-wider">Select a candidate answer from the left log to view coaching reviews.</p>
                  </div>
                )}
              </div>

            </div>
          </div>
        )}

        {/* VIEW 6: ADMIN PANEL */}
        {view === "admin" && (
          <div className="space-y-8 py-4">
            <div className="border border-zinc-800 rounded p-6 bg-zinc-950/40 space-y-2">
              <h2 className="text-2xl font-bold tracking-tight text-neutral-100">
                SYSTEM.ANALYTICS
              </h2>
              <p className="text-xs text-neutral-400 font-light">
                Monitoring cluster metrics, user volume, recommendation distribution, and API pipelines.
              </p>
            </div>

            {adminStats ? (
              <div className="space-y-6">
                {/* Stats cards grid */}
                <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                  <div className="border border-zinc-900 p-5 rounded bg-zinc-950/10 flex flex-col space-y-1">
                    <span className="text-[9px] uppercase tracking-widest text-zinc-500">Registered Users</span>
                    <span className="text-2xl font-bold font-mono text-neutral-200">{adminStats.total_users}</span>
                  </div>
                  <div className="border border-zinc-900 p-5 rounded bg-zinc-950/10 flex flex-col space-y-1">
                    <span className="text-[9px] uppercase tracking-widest text-zinc-500">Interviews Initiated</span>
                    <span className="text-2xl font-bold font-mono text-neutral-200">{adminStats.total_sessions}</span>
                  </div>
                  <div className="border border-zinc-900 p-5 rounded bg-zinc-950/10 flex flex-col space-y-1">
                    <span className="text-[9px] uppercase tracking-widest text-zinc-500">Completed Sessions</span>
                    <span className="text-2xl font-bold font-mono text-neutral-200">{adminStats.completed_sessions}</span>
                  </div>
                  <div className="border border-zinc-900 p-5 rounded bg-zinc-950/10 flex flex-col space-y-1">
                    <span className="text-[9px] uppercase tracking-widest text-zinc-500">Average Readiness Index</span>
                    <span className="text-2xl font-bold font-mono text-neutral-200">{Math.round(adminStats.average_readiness_score)}%</span>
                  </div>
                </div>

                {/* Recommendation breakdown */}
                <div className="grid grid-cols-1 md:grid-cols-12 gap-6">
                  
                  {/* Left Column: Recommendations */}
                  <div className="md:col-span-5 border border-zinc-900 p-6 rounded bg-zinc-950/10 space-y-4">
                    <h4 className="text-xs uppercase tracking-widest font-semibold text-neutral-300 pb-2 border-b border-zinc-900">
                      Recommendation Breakdown.
                    </h4>
                    <div className="space-y-3 text-xs">
                      {Object.keys(adminStats.recommendation_distribution).length > 0 ? (
                        Object.entries(adminStats.recommendation_distribution).map(([rec, count]: [string, any]) => (
                          <div key={rec} className="flex items-center justify-between">
                            <span className="text-neutral-400 uppercase font-mono">{rec.replace("_", " ")}</span>
                            <span className="text-neutral-200 font-semibold">{count} sessions</span>
                          </div>
                        ))
                      ) : (
                        <div className="text-zinc-600 font-light">No sessions scored yet.</div>
                      )}
                    </div>
                  </div>

                  {/* Right Column: Recent Sessions */}
                  <div className="md:col-span-7 border border-zinc-900 p-6 rounded bg-zinc-950/10 space-y-4">
                    <h4 className="text-xs uppercase tracking-widest font-semibold text-neutral-300 pb-2 border-b border-zinc-900">
                      Active Interview Queues.
                    </h4>
                    <div className="overflow-x-auto">
                      <table className="w-full text-xs text-left">
                        <thead>
                          <tr className="border-b border-zinc-900 text-zinc-500">
                            <th className="pb-2 font-medium uppercase tracking-wider">User</th>
                            <th className="pb-2 font-medium uppercase tracking-wider">Role Track</th>
                            <th className="pb-2 font-medium uppercase tracking-wider">Status</th>
                            <th className="pb-2 font-medium uppercase tracking-wider">Score</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-zinc-900 font-light">
                          {adminStats.recent_sessions.map((s: any) => (
                            <tr key={s.id}>
                              <td className="py-2 text-neutral-300">{s.email}</td>
                              <td className="py-2 text-neutral-400 font-mono uppercase">{s.role_track}</td>
                              <td className="py-2">
                                <span className={`px-1.5 py-0.5 rounded text-[9px] uppercase font-mono ${
                                  s.status === "completed" ? "bg-emerald-950/20 text-emerald-400" : "bg-yellow-950/20 text-yellow-400"
                                }`}>
                                  {s.status}
                                </span>
                              </td>
                              <td className="py-2 text-neutral-200 font-mono">{s.readiness_score ? `${Math.round(s.readiness_score)}%` : "N/A"}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>

                </div>
              </div>
            ) : (
              <div className="h-40 flex items-center justify-center">
                <RefreshCw className="w-6 h-6 text-zinc-500 animate-spin" />
              </div>
            )}

            <div className="flex justify-center">
              <button 
                onClick={() => setView("landing")}
                className="border border-zinc-800 hover:bg-zinc-900 text-neutral-300 font-semibold py-3 px-6 rounded text-xs uppercase tracking-widest transition-colors cursor-pointer"
              >
                Return to Platform
              </button>
            </div>
          </div>
        )}

      </main>

      {/* Footer */}
      <footer className="border-t border-zinc-800 bg-[#0a0a0a] px-6 py-4 flex flex-col md:flex-row items-center justify-between text-[10px] text-zinc-500 uppercase tracking-widest font-light space-y-2 md:space-y-0">
        <span>© 2026 Eval Systems Inc. All rights reserved.</span>
        <div className="flex space-x-6">
          <a href="#" className="hover:text-neutral-300">Security.</a>
          <a href="#" className="hover:text-neutral-300">Architecture Schema.</a>
          <a href="#" className="hover:text-neutral-300">Hiring Committee guidelines.</a>
        </div>
      </footer>
    </div>
  );
}
