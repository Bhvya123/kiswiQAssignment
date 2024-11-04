FROM python:3.11

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

RUN apt-get update && \
    apt-get install -y default-mysql-server && \
    apt-get clean

COPY . .

COPY start.sh /start.sh
RUN chmod +x /start.sh

EXPOSE 3306

EXPOSE 8000

CMD ["/start.sh"]
