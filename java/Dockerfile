FROM maven:3.9-eclipse-temurin-21 AS builder
WORKDIR /app
COPY pom.xml ./
COPY common/pom.xml common/
COPY auth/pom.xml auth/
COPY document/pom.xml document/
COPY chat/pom.xml chat/
COPY audit/pom.xml audit/
# Download dependencies first (cache layer)
RUN mvn dependency:go-offline -pl common,auth,document,chat,audit -q || true
COPY common/src common/src/
COPY auth/src auth/src/
COPY document/src document/src/
COPY chat/src chat/src/
COPY audit/src audit/src/
RUN mvn clean package -DskipTests -pl common,auth,document,chat,audit -q

FROM eclipse-temurin:21-jre
WORKDIR /app
COPY --from=builder /app/auth/target/*.jar auth.jar
COPY --from=builder /app/document/target/*.jar document.jar
COPY --from=builder /app/chat/target/*.jar chat.jar
COPY --from=builder /app/audit/target/*.jar audit.jar
COPY docker-entrypoint.sh /app/docker-entrypoint.sh
RUN chmod +x /app/docker-entrypoint.sh
EXPOSE 8080 8081 8082 8083
ENTRYPOINT ["/app/docker-entrypoint.sh"]
