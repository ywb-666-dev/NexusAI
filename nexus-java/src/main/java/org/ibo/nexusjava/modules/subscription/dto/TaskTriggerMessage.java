package org.ibo.nexusjava.modules.subscription.dto;

import lombok.Data;

/**
 * @author: yi327
 * @date: 2026/5/27
 */
@Data
public class TaskTriggerMessage {
    private String taskId;
    private Long subscriptionId;
    private String triggerTime;
}
