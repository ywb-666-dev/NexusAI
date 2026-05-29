package org.ibo.nexusjava.modules.notification.vo;

import lombok.Data;

import java.time.LocalDateTime;

@Data
public class NotificationVO {
    private Long id;
    private Long userId;
    private String type;
    private String title;
    private String content;
    private Integer isRead;
    private String relatedId;
    private LocalDateTime createdAt;
}
