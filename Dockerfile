FROM python:3.13-slim

RUN useradd -m -u 1000 user
USER user
ENV PATH="/home/user/.local/bin:$PATH"
WORKDIR /home/user/app

COPY --chown=user requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

COPY --chown=user . .

ENV RNV_PALETTE_STORE=/home/user/app/data/palettes.json
ENV PORT=7860
EXPOSE 7860

CMD ["python", "server.py"]
