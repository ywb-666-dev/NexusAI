package org.ibo.nexusjava.messaging.dto;

import lombok.Data;

@Data
public class DeadLetterMessage {
    private String originalTopic;
    private String originalMessage;
    private String failureReason;
    private String retryCount;
}
