/* Click-to-speak text capture using the browser's own speech recognition —
   no server round-trip, no audio file ever leaves the machine. Recognized
   text is held as a draft the doctor must explicitly insert; nothing is
   written into the field being dictated into until they accept it, so a
   misheard word never lands unreviewed. Chrome/Edge only (webkitSpeechRecognition) —
   the button simply doesn't render where the API is unavailable, rather than
   pretending to work and silently doing nothing. */

import { useEffect, useRef, useState } from "react";

const SpeechRecognitionCtor =
  typeof window !== "undefined" ? window.SpeechRecognition || window.webkitSpeechRecognition : null;

export default function VoiceInput({ onInsert, lang = "en-IN" }) {
  const [listening, setListening] = useState(false);
  const [draft, setDraft] = useState("");
  const [error, setError] = useState("");
  const recognitionRef = useRef(null);

  useEffect(() => () => recognitionRef.current?.stop(), []);

  if (!SpeechRecognitionCtor) return null;

  function start() {
    setError("");
    setDraft("");
    const recognition = new SpeechRecognitionCtor();
    recognition.lang = lang;
    recognition.continuous = true;
    recognition.interimResults = true;
    recognition.onresult = (e) => {
      let text = "";
      for (let i = 0; i < e.results.length; i++) text += e.results[i][0].transcript;
      setDraft(text.trim());
    };
    recognition.onerror = (e) => {
      setError(e.error === "not-allowed" ? "Microphone access was blocked." : "Could not hear that clearly — try again.");
      setListening(false);
    };
    recognition.onend = () => setListening(false);
    recognitionRef.current = recognition;
    recognition.start();
    setListening(true);
  }

  function stop() {
    recognitionRef.current?.stop();
  }

  function insert() {
    if (draft.trim()) onInsert(draft.trim());
    setDraft("");
  }

  return (
    <div className="voice-input">
      <button type="button" className={`btn voice-mic ${listening ? "listening" : ""}`} onClick={listening ? stop : start}>
        <span className="voice-dot" aria-hidden="true" />
        {listening ? "Listening — tap to stop" : "Speak"}
      </button>

      {error ? <p className="form-error" role="alert">{error}</p> : null}

      {draft ? (
        <div className="voice-draft">
          <p className="voice-draft-text">{draft}</p>
          {!listening ? (
            <div className="voice-draft-actions">
              <button type="button" className="btn btn-primary" onClick={insert}>Insert</button>
              <button type="button" className="btn" onClick={start}>Try again</button>
              <button type="button" className="btn" onClick={() => setDraft("")}>Discard</button>
            </div>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}
