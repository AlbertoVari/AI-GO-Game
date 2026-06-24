import cv2
import base64
import subprocess
import threading
import queue
import time
import sounddevice as sd
import numpy as np
from faster_whisper import WhisperModel
from langchain_ollama import ChatOllama
from langchain_core.messages import HumanMessage, SystemMessage
import os

# =====================================================================
# CONFIGURAZIONI GLOBALI
# =====================================================================
coda_frame = queue.Queue(maxsize=1)
ia_in_funzione = False
partita_iniziata = False
colore_utente = None
running = True

# =====================================================================
# MODULO 1: VISIONE AI (Ollama Windows da WSL2)
# =====================================================================
MODELLO_VISION = "qwen3-vl:8b"

# Risolve dinamicamente l'IP di gateway WSL2 → Windows (più stabile di IP statico)
DEFAULT_HOST_IP = os.popen("ip route | grep default | awk '{print $3}'").read().strip() or "172.22.240.1"

print(f"[🌐] Connessione Ollama Windows: http://{DEFAULT_HOST_IP}:11434 ...")
llm = ChatOllama(
    model=MODELLO_VISION,
    temperature=0.1,
    base_url=f"http://{DEFAULT_HOST_IP}:11434"
)

storico_partita = [
    SystemMessage(content=(
        "Sei un assistente e giocatore di Go esperto. Giochiamo su un Goban ridotto 9x9. "
        "Le righe e le colonne usano i numeri da 1 a 9 e le lettere da A a J (escludendo la I). "
        "Analizza attentamente la foto della scacchiera. "
        "Decidi la tua contromossa, esprimi le coordinate esatte (es. E5, G3) "
        "e spiega la mossa in una sola frase breve e colloquiale in italiano. "
        "Se ti viene chiesto di fare la prima mossa come Nero, proponi un'apertura standard (es. G7 o G3)."
    ))
]

def elabora_mossa_ai(frame_scatto=None, prima_mossa_assoluta=False):
    if prima_mossa_assoluta:
        contenuto = [{"type": "text", "text": "Inizia tu la partita come Nero sul Goban 9x9. Dimmi la tua prima mossa."}]
    else:
        _, buffer = cv2.imencode('.jpg', frame_scatto)
        b64_image = base64.b64encode(buffer).decode('utf-8')
        contenuto = [
            {"type": "text", "text": "Ho fatto la mia mossa. Guarda la scacchiera e dimmi la tua mossa."},
            {"type": "image_url", "image_url": f"data:image/jpeg;base64,{b64_image}"}
        ]

    storico_partita.append(HumanMessage(content=contenuto))
    try:
        risposta = llm.invoke(storico_partita)
        storico_partita.append(risposta)
        return risposta.content
    except Exception as e:
        return f"Errore Ollama: {str(e)}"

# =====================================================================
# MODULO 2: SINTESI VOCALE (Piper TTS → Speaker Stereo WSLg)
# =====================================================================
def parla_piper(testo):
    piper_bin = "/home/olivaw/ai-lab/piper/piper"
    modello_piper = "/home/olivaw/ai-lab/it_IT-paola-medium.onnx"
    
    # Usa paplay invece di aplay - è nativo per PulseAudio
    cmd = f'echo "{testo}" | {piper_bin} --model {modello_piper} --output_file - | paplay --raw --rate=22050 --channels=1 --format=s16le'
    
    subprocess.Popen(cmd, shell=True)

# =====================================================================
# FUNZIONE DI SUPPORTO 
# =====================================================================
def _processa_turno(frame):
    global ia_in_funzione
    resp = elabora_mossa_ai(frame_scatto=frame)
    print(f"🤖 Risposta IA: {resp}")
    parla_piper(resp)
    ia_in_funzione = False


# =====================================================================
# MODULO 3: ASCOLTO VOCALE (Faster-Whisper in background)
# =====================================================================
def thread_ascolto_vocale():
    global ia_in_funzione, partita_iniziata, colore_utente
    print("\n[️] Caricamento Whisper Tiny (CPU)...")
    stt_model = WhisperModel("tiny", device="cpu", compute_type="int8", cpu_threads=4)

    SR = 16000
    BLOCK_SEC = 3.0  # Aumentato a 3 secondi per dare più tempo

    # 🎯 FORZA L'USO DEL DISPOSITIVO "pulse" (index 1)
    sd.default.device[0] = 1
    print("[🎤] Microfono selezionato: pulse (WSLg audio bridge)")

    print("[🔊] Routing audio WSL2 → Speaker Realtek pronto.")
    time.sleep(2)

    parla_piper("Benvenuto sul Goban 9x9. Scegli il colore: Bianco o Nero?")
    print("[🎙️] Parla dal microfono. Dì 'Bianco' o 'Nero'.")

    while not partita_iniziata:
        try:
            audio = sd.rec(int(BLOCK_SEC * SR), samplerate=SR, channels=1, dtype='int16')
            sd.wait()
            
            audio_np = audio.flatten().astype(np.float32) / 32768.0
            
            # DEBUG: Verifica il volume
            rms = np.sqrt(np.mean(audio_np**2))
            print(f"[ DEBUG] Volume: {rms:.4f}", end=" ")
            
            if rms < 0.01:
                print("→ [Silenzio, riprova]")
                continue
            
            segments, _ = stt_model.transcribe(audio_np, language="it")
            testo = " ".join([s.text for s in segments]).lower().strip()
            
            if testo:
                print(f"→ Whisper: '{testo}'")
            else:
                print("→ [Non riconosciuto]")

            if "bianco" in testo:
                colore_utente, partita_iniziata = "bianco", True
                print("[🎲] Scelta: Bianco. Prima mossa IA...")
                parla_piper("Hai scelto il Bianco. Tocca a me come Nero.")
                time.sleep(1)
                ia_in_funzione = True
                resp = elabora_mossa_ai(prima_mossa_assoluta=True)
                print(f"🤖 Mossa: {resp}")
                parla_piper(resp)
                ia_in_funzione = False

            elif "nero" in testo:
                colore_utente, partita_iniziata = "nero", True
                print("[🎲] Scelta: Nero. L'utente inizia.")
                parla_piper("Hai scelto il Nero. Posiziona la pietra e poi dì 'mia mossa'.")

        except Exception as e:
            print(f"[⚠️ STT Error: {e}]")
            time.sleep(1)

    print("\n[️] In ascolto. Dì 'mia mossa' per scattare foto alla scacchiera.")
    while True:
        try:
            audio = sd.rec(int(BLOCK_SEC * SR), samplerate=SR, channels=1, dtype='int16')
            sd.wait()
            
            audio_np = audio.flatten().astype(np.float32) / 32768.0
            
            rms = np.sqrt(np.mean(audio_np**2))
            if rms < 0.01:
                continue
            
            segments, _ = stt_model.transcribe(audio_np, language="it")
            testo = " ".join([s.text for s in segments]).lower().strip()

            if "mia mossa" in testo and not ia_in_funzione:
                print("\n[️] Comando rilevato!")
                ia_in_funzione = True
                if not coda_frame.empty():
                    frame = coda_frame.get()
                    threading.Thread(target=_processa_turno, args=(frame,), daemon=True).start()
        except Exception as e:
            print(f"[⚠️ Audio Loop Error: {e}]")
            time.sleep(1)

# =====================================================================
# MODULO 4: STREAMING VIDEO (WSLg webcam passthrough → OpenCV)
# =====================================================================
def avvia_interfaccia_gioco():
    global ia_in_funzione, partita_iniziata, colore_utente

    # Forza backend V4L2 per compatibilità con WSLg/usbipd
    os.environ['OPENCV_VIDEOIO_PRIORITY_MSMF'] = '0'
    cap = cv2.VideoCapture(0)

    if not cap.isOpened():
        print("❌ Webcam non trovata. Su Windows 11 ≥22631 è montata in /dev/video0.")
        print("   Altrimenti: `usbipd wsl attach --bus <BUS-ID>` da PowerShell admin.")
        return

    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

    threading.Thread(target=thread_ascolto_vocale, daemon=True).start()
    print("[🖥️] Avvio interfaccia. Premi 'Q' per uscire.")

    while True:
        ret, frame = cap.read()
        if not ret: break

        if coda_frame.full():
            try: coda_frame.get_nowait()
            except queue.Empty: pass
        coda_frame.put(frame)

        if not partita_iniziata:
            cv2.putText(frame, "SCEGLI IL COLORE A VOCE...", (15, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 165, 255), 2)
        elif ia_in_funzione:
            cv2.putText(frame, "IA: Calcolo mossa su Windows...", (15, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
        else:
            cv2.putText(frame, f"Giochi come: {colore_utente.upper()}", (15, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)
            cv2.putText(frame, "Dici 'mia mossa' per passare il turno", (15, 70), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

        cv2.imshow("Goban 9x9 AI WSL2", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'): break
            # --- NUOVO BLOCCO DI CHIUSURA ---
    global running
    running = False
    time.sleep(0.5) # Dai il tempo al thread audio di uscire da sd.wait()
    
    cap.release()
    cv2.destroyAllWindows()
    sd.stop()
   
if __name__ == "__main__":
    try:
        avvia_interfaccia_gioco()
    except KeyboardInterrupt:
        print("\n[🛑] Uscita manuale.")
    finally:
        sd.stop()
        cv2.destroyAllWindows()
