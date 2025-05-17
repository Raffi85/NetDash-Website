# 🌐 Fullstack Product Website – Deployment Guide

## 📦 Requirements
- Docker installed
- Docker Compose installed

## 🛠 How to Run the Project

1. **Unzip and navigate to the folder**
   ```bash
   unzip productWebsite.zip
   cd productWebsite
   ```

2. **Start everything using Docker Compose**
   ```bash
   docker-compose up --build
   ```

3. **Access the app:**
   - Frontend: http://localhost
   - Backend API: http://localhost:5000

4. **MariaDB:**
   - Host: localhost
   - Port: 3306
   - DB: yourdbname
   - User: youruser
   - Pass: yourpass

5. **Stop the project**
   ```bash
   docker-compose down
   ```

## 🧪 Initial DB Setup
If you need to import the database manually:
```bash
docker exec -i $(docker ps -qf "name=mariadb") \
  mysql -uyouruser -pyourpass yourdbname < backend/product_website_schema.sql
```