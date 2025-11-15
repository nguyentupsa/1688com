FROM node:18-bullseye-slim

WORKDIR /app

# Chỉ copy manifest để cache layer
COPY package*.json ./

# Cài deps bên trong container.
# Nếu lockfile của bạn sinh trên Windows gây lỗi Rollup => fallback sang npm i sạch
RUN (npm ci) || (rm -rf node_modules package-lock.json && npm i --no-audit --no-fund)

# Copy source code
COPY . .

EXPOSE 5173

# Vite phải bind 0.0.0.0 trong container
CMD ["npm","run","dev","--","--host","0.0.0.0","--port","5173"]
