package org.ibo.nexusjava.messaging.consumer;

import lombok.extern.slf4j.Slf4j;
import org.apache.rocketmq.spring.annotation.RocketMQMessageListener;
import org.apache.rocketmq.spring.core.RocketMQListener;
import org.ibo.nexusjava.messaging.dto.TaskTriggerMessage;
import org.ibo.nexusjava.modules.subscription.entity.Subscription;
import org.ibo.nexusjava.modules.subscription.mapper.SubscriptionMapper;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Component;

import java.time.LocalDateTime;

@Slf4j
@Component
@RocketMQMessageListener(
        topic = "nexus-task-trigger",
        consumerGroup = "nexus-java-task-trigger-consumers"
)
public class TaskTriggerConsumer implements RocketMQListener<TaskTriggerMessage> {

    @Autowired
    private SubscriptionMapper subscriptionMapper;

    @Override
    public void onMessage(TaskTriggerMessage message) {
        log.info("[TaskTrigger] 收到任务触发消息: taskId={}, subscriptionId={}",
                message.getTaskId(), message.getSubscriptionId());

        Subscription update = new Subscription();
        update.setId(message.getSubscriptionId());
        update.setLastRunAt(LocalDateTime.now());
        subscriptionMapper.updateById(update);

        log.info("[TaskTrigger] 已更新 subscription.last_run_at: subscriptionId={}", message.getSubscriptionId());
    }
}
