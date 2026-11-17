# Dashboard Streamlit. Image chỉ chứa app + số liệu tổng hợp công khai, không có nội dung JD.
FROM python:3.12-slim
WORKDIR /app
RUN pip install --no-cache-dir streamlit==1.67.0
COPY app.py .
COPY data/public/ data/public/
EXPOSE 8501
HEALTHCHECK CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8501/_stcore/health')"
CMD ["streamlit", "run", "app.py", "--server.address=0.0.0.0", "--server.headless=true"]
