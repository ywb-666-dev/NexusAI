import { useEffect, useRef, useState } from "react";

export function chunks(text: string) {
  const result: string[] = [];
  for (const sentence of text.match(/[^。！？.!?\n]+[。！？.!?\n]*/g) || []) {
    const chars = Array.from(sentence.trim());
    while (chars.length) result.push(chars.splice(0, 140).join(""));
  }
  return result;
}

export default function useRadioSpeech(
  texts: string[],
  onEvent: (index: number) => void,
  checkpoint: (event: number, part: number) => void,
) {
  const [voices, setVoices] = useState<SpeechSynthesisVoice[]>([]),
    [voice, setVoice] = useState(""),
    [rate, setRate] = useState(1);
  const [state, setState] = useState("stopped"),
    [spoken, setSpoken] = useState(""),
    [error, setError] = useState("");
  const generation = useRef(0),
    cursor = useRef({ event: 0, part: 0 }),
    utterance = useRef<SpeechSynthesisUtterance | null>(null);
  const handlers = useRef({ texts, onEvent, checkpoint, voice, rate });
  handlers.current = { texts, onEvent, checkpoint, voice, rate };
  const supported =
    typeof window !== "undefined" && "speechSynthesis" in window;
  const stop = () => {
    generation.current++;
    if (supported) window.speechSynthesis.cancel();
    utterance.current = null;
    setState("stopped");
  };
  const pause = () => {
    if (supported) window.speechSynthesis.pause();
    setState((previous) => (previous === "playing" ? "paused" : previous));
  };
  const play = (event: number, part = 0) => {
    if (!supported || !window.speechSynthesis.getVoices().length) {
      setError("当前设备没有可用朗读声音，可以继续看卡片和文字追问。");
      return;
    }
    generation.current++;
    const ticket = generation.current;
    window.speechSynthesis.cancel();
    window.speechSynthesis.resume();
    setError("");
    const step = (eventIndex: number, partIndex: number) => {
      if (ticket !== generation.current) return;
      const {
        texts: currentTexts,
        onEvent: select,
        checkpoint: save,
      } = handlers.current;
      if (eventIndex >= currentTexts.length) {
        setState("ended");
        setSpoken("");
        return;
      }
      const parts = chunks(currentTexts[eventIndex]);
      if (partIndex >= parts.length) {
        step(eventIndex + 1, 0);
        return;
      }
      cursor.current = { event: eventIndex, part: partIndex };
      select(eventIndex);
      save(eventIndex, partIndex);
      const u = new SpeechSynthesisUtterance(parts[partIndex]);
      utterance.current = u;
      const available = window.speechSynthesis.getVoices();
      u.voice =
        available.find((v) => v.voiceURI === handlers.current.voice) ||
        available.find((v) => /^zh/i.test(v.lang)) ||
        available[0];
      u.lang = u.voice?.lang || "zh-CN";
      u.rate = handlers.current.rate;
      u.onstart = () => {
        if (ticket === generation.current) {
          setState("playing");
          setSpoken(parts[partIndex]);
        }
      };
      u.onend = () => {
        if (ticket === generation.current) step(eventIndex, partIndex + 1);
      };
      u.onerror = (e) => {
        if (
          ticket === generation.current &&
          e.error !== "canceled" &&
          e.error !== "interrupted"
        ) {
          setState("stopped");
          setError(
            "朗读未能继续，请检查设备声音或重新播放；文字阅读仍可使用。",
          );
        }
      };
      setState("playing");
      window.speechSynthesis.speak(u);
    };
    step(event, part);
  };
  const resume = () => {
    if (!supported) return;
    if (window.speechSynthesis.speaking && window.speechSynthesis.paused) {
      window.speechSynthesis.resume();
      setState("playing");
    } else play(cursor.current.event, cursor.current.part);
  };
  useEffect(() => {
    if (!supported) return;
    const update = () => setVoices(window.speechSynthesis.getVoices());
    update();
    window.speechSynthesis.addEventListener("voiceschanged", update);
    const hidden = () => {
      if (document.hidden) pause();
    };
    document.addEventListener("visibilitychange", hidden);
    return () => {
      generation.current++;
      window.speechSynthesis.cancel();
      utterance.current = null;
      window.speechSynthesis.removeEventListener("voiceschanged", update);
      document.removeEventListener("visibilitychange", hidden);
    };
  }, []);
  return {
    voices,
    voice,
    setVoice,
    rate,
    setRate,
    state,
    spoken,
    error,
    supported,
    play,
    pause,
    resume,
    stop,
  };
}
