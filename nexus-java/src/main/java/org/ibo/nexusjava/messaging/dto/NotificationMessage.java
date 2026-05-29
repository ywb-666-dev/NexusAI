package org.ibo.nexusjava.messaging.dto;

import lombok.Data;

@Data
public class NotificationMessage {
    private Long userId;
    private String type;
    private String title;
    private String content;
    private String relatedId;
}
