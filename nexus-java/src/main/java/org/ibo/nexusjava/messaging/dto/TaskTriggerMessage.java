package org.ibo.nexusjava.messaging.dto;

import lombok.Data;

@Data
public class TaskTriggerMessage {
    private String taskId;
    private Long subscriptionId;
    private String triggerTime;
}
