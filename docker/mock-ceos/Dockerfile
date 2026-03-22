FROM python:3.11-slim

RUN pip install --no-cache-dir paramiko

COPY mock_ceos.py /mock_ceos.py

EXPOSE 22

CMD ["python", "/mock_ceos.py"]
