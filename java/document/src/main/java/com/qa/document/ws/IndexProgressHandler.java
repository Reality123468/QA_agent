package com.qa.document.ws;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Component;
import org.springframework.web.reactive.socket.WebSocketHandler;
import org.springframework.web.reactive.socket.WebSocketSession;
import reactor.core.publisher.Mono;
import reactor.core.publisher.Sinks;

import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;

@Component
public class IndexProgressHandler implements WebSocketHandler {

    private static final Logger log = LoggerFactory.getLogger(IndexProgressHandler.class);

    private final Map<String, WebSocketSession> sessions = new ConcurrentHashMap<>();
    private final ObjectMapper objectMapper;

    public IndexProgressHandler(ObjectMapper objectMapper) {
        this.objectMapper = objectMapper;
    }

    @Override
    public Mono<Void> handle(WebSocketSession session) {
        sessions.put(session.getId(), session);
        log.info("WebSocket connected: {}", session.getId());

        return session.receive()
                .doFinally(sig -> {
                    sessions.remove(session.getId());
                    log.info("WebSocket disconnected: {}", session.getId());
                })
                .then();
    }

    public void broadcastProgress(Long docId, String status, String message) {
        try {
            String payload = objectMapper.writeValueAsString(Map.of(
                    "docId", docId,
                    "status", status,
                    "message", message
            ));
            for (WebSocketSession session : sessions.values()) {
                if (session.isOpen()) {
                    session.send(Mono.just(session.textMessage(payload)))
                            .subscribe(
                                    null,
                                    err -> {
                                        log.warn("Failed to send WS message to {}", session.getId(), err);
                                        sessions.remove(session.getId());
                                    }
                            );
                }
            }
        } catch (JsonProcessingException e) {
            log.error("Failed to serialize progress message", e);
        }
    }
}
