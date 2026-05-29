package org.ibo.nexusjava.messaging.dto;

import lombok.Data;

import java.time.LocalDateTime;

@Data
public class ContentParsedMessage {
    private String taskId;
    private Long subscriptionId;
    private String sourcePlatform;
    private String sourceUrl;
    private String title;
    private String summary;
    private String contentBody;
    private String author;
    private LocalDateTime publishedAt;
    private String contentHash;
    private String vectorId;
}
