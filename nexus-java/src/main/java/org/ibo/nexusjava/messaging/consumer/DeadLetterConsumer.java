package org.ibo.nexusjava.messaging.consumer;

import lombok.extern.slf4j.Slf4j;
import org.apache.rocketmq.spring.annotation.RocketMQMessageListener;
import org.apache.rocketmq.spring.core.RocketMQListener;
import org.ibo.nexusjava.messaging.dto.DeadLetterMessage;
import org.ibo.nexusjava.modules.audit.entity.AuditLog;
import org.ibo.nexusjava.modules.audit.mapper.AuditLogMapper;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.stereotype.Component;

import java.time.LocalDateTime;

@Slf4j
@Component
@ConditionalOnProperty(name = "rocketmq.enabled", havingValue = "true")
@RocketMQMessageListener(
        topic = "nexus-dead-letter",
        consumerGroup = "nexus-java-dead-letter-consumers"
)
public class DeadLetterConsumer implements RocketMQListener<DeadLetterMessage> {

    @Autowired
    private AuditLogMapper auditLogMapper;

    @Override
    public void onMessage(DeadLetterMessage message) {
        log.warn("[DeadLetter] 收到死信消息: originalTopic={}, failureReason={}",
                message.getOriginalTopic(), message.getFailureReason());

        AuditLog logEntry = new AuditLog();
        logEntry.setAction("DEAD_LETTER");
        logEntry.setTargetType(message.getOriginalTopic());
        logEntry.setTargetId(message.getOriginalMessage());
        logEntry.setActionTime(LocalDateTime.now());
        logEntry.setIpAddress("system");
        logEntry.setRequestId(message.getRetryCount());

        auditLogMapper.insert(logEntry);

        log.info("[DeadLetter] 死信已记录到 audit_log: auditLogId={}", logEntry.getId());
    }
}
