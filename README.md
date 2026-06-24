# AI-GO-Game
Assistente AI completo per giocare a Go su goban 9x9, combinando visione artificiale, riconoscimento vocale e sintesi vocale

✨ Caratteristiche
🎯 Gioco hands-free: Controlla il gioco con la voce ("Bianco", "Nero", "mia mossa")
👁️ Visione AI: Qwen3-VL analizza la scacchiera tramite webcam e suggerisce mosse strategiche
🗣️ Interazione vocale bidirezionale:
Whisper Tiny per il riconoscimento vocale in italiano
Piper TTS per risposte vocali naturali con voce italiana (Paola)
⚡ Prestazioni ottimizzate: Inferenza GPU su AMD Radeon 780M (~15-25 secondi per mossa)
🖥️ Architettura ibrida: WSL2 + Windows con routing audio/video trasparente

📋 Requisiti
Hardware
GPU: AMD Radeon 780M o superiore (consigliati 16GB VRAM)
RAM: 16GB minimo, 32GB consigliati
Webcam: Compatibile con WSLg o USB/IP
Microfono: Qualsiasi microfono funzionante su Windows

Software
Windows 11 (build 22631 o superiore per WSLg)
WSL2 con Ubuntu 24.04
Ollama installato su Windows
Python 3.12+

Flusso di gioco
Selezione colore: Di' "Bianco" o "Nero" al microfono
Partita:
Se giochi Nero: Posiziona la pietra sul goban e di' "mia mossa"
Se giochi Bianco: L'IA inizia come Nero
Analisi: L'IA analizza la scacchiera via webcam e suggerisce la mossa
Uscita: Premi Q nella finestra video

📄 License
MIT License - vedi file LICENSE per dettagli.
🤝 Contributi
I contributi sono benvenuti! Sentiti libero di aprire issue o pull request.

🙏 Ringraziamenti

Qwen Team per il modello Qwen3-VL

Ollama per l'inferenza locale semplificata

Rhasspy/Piper per la sintesi vocale offline

OpenAI/Whisper per il riconoscimento vocale

Comunità WSL per il supporto audio/video su WSLg


Buon Go! 🎮⚫
"Il Go è l'unico gioco in cui anche dopo aver perso, hai imparato qualcosa."
