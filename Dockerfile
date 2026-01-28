# Usa Python 3.9 slim per leggerezza
FROM python:3.9-slim

# Variabili d'ambiente
ENV PYTHONUNBUFFERED=1
# Impedisce la creazione di file .pyc inutili
ENV PYTHONDONTWRITEBYTECODE=1

# 1. Installazione dipendenze di sistema necessarie per la compilazione
RUN apt-get update && apt-get install -y \
    git \
    build-essential \
    wget \
    && rm -rf /var/lib/apt/lists/*

# 2. Compilazione RTKLIB (Layer separato per pulizia successiva)
WORKDIR /tmp
RUN git clone https://github.com/rtklibexplorer/RTKLIB.git \
    && cd RTKLIB \
    && git checkout b28b5ac55018f17d352b59bb73bb0951888885cb \
    && cd app/consapp/rtkrcv/gcc \
    && make

# 3. Setup Applicazione
WORKDIR /app

# Copiamo prima i requirements per sfruttare la cache dei layer Docker
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiamo tutto il codice sorgente
COPY . .

# 4. Spostiamo l'eseguibile rtkrcv nella cartella del progetto
# Crea la cartella se non esiste e sposta il file compilato
RUN mkdir -p rtklib \
    && cp /tmp/RTKLIB/app/consapp/rtkrcv/gcc/rtkrcv /app/rtklib/rtkrcv \
    && chmod +x /app/rtklib/rtkrcv

# Puliamo i file temporanei di compilazione
RUN rm -rf /tmp/RTKLIB

# 5. Configurazione Porta e Avvio
# Dichiariamo che il container ascolta sulla 5000
EXPOSE 5000

# IMPORTANTE: Sostituisci 'tuo_file_start.py' con il nome reale del tuo file python (es. app.py, main.py)
CMD ["python", "app.py"]
