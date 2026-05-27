package org.ibo.nexusjava.modules.subscription.service.impl;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.core.metadata.IPage;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.baomidou.mybatisplus.extension.service.impl.ServiceImpl;
import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.apache.rocketmq.client.producer.SendResult;
import org.apache.rocketmq.client.producer.SendStatus;
import org.apache.rocketmq.spring.core.RocketMQTemplate;
import org.ibo.nexusjava.common.BusinessException;
import org.ibo.nexusjava.common.ErrorCode;
import org.ibo.nexusjava.interceptor.UserContext;
import org.ibo.nexusjava.modules.subscription.dto.SubscriptionDTO;
import org.ibo.nexusjava.modules.subscription.dto.SubscriptionQueryDTO;
import org.ibo.nexusjava.modules.subscription.dto.TaskTriggerMessage;
import org.ibo.nexusjava.modules.subscription.entity.Subscription;
import org.ibo.nexusjava.modules.subscription.mapper.SubscriptionMapper;
import org.ibo.nexusjava.modules.subscription.service.SubscriptionService;
import org.ibo.nexusjava.modules.subscription.vo.SubscriptionVO;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.stereotype.Service;
import org.springframework.util.StringUtils;

import java.time.LocalDateTime;
import java.util.Collections;
import java.util.List;
import java.util.UUID;
import java.util.concurrent.TimeUnit;
import java.util.stream.Collectors;

@Service
public class SubscriptionServiceImpl extends ServiceImpl<SubscriptionMapper, Subscription> implements SubscriptionService {

    private final ObjectMapper objectMapper=new ObjectMapper();

    @Autowired
    private RocketMQTemplate rocketMQTemplate;

    @Autowired
    private StringRedisTemplate stringRedisTemplate;

    private static final String LOCK_PREFIX = "lock:subscription:";
    private static final long LOCK_TIMEOUT = 300; // 5分钟，与 Scout Agent 最大执行时间匹配

    // ==================== JSON 转换工具方法 ====================

    private String toJson(List<String> list) {
        if (list == null || list.isEmpty()) return "[]";
        try {
            return objectMapper.writeValueAsString(list);
        } catch (JsonProcessingException e) {
            throw new BusinessException(ErrorCode.PARAM_ERROR, "JSON序列化失败");
        }
    }

    private List<String> fromJson(String json) {
        if (!StringUtils.hasText(json)) return Collections.emptyList();
        try {
            return objectMapper.readValue(json, new TypeReference<List<String>>() {});
        } catch (JsonProcessingException e) {
            throw new BusinessException(ErrorCode.SYSTEM_ERROR, "JSON反序列化失败");
        }
    }

    private SubscriptionVO convertToVO(Subscription sub) {
        SubscriptionVO vo = new SubscriptionVO();
        vo.setId(sub.getId());
        vo.setName(sub.getName());
        vo.setKeywords(fromJson(sub.getKeywords()));
        vo.setSourcePlatforms(fromJson(sub.getSourcePlatforms()));
        vo.setMatchMode(sub.getMatchMode());
        vo.setTriggerConditions(sub.getTriggerConditions());
        vo.setPriority(sub.getPriority());
        vo.setStatus(sub.getStatus());
        vo.setCronExpression(sub.getCronExpression());
        vo.setLastRunAt(sub.getLastRunAt());
        vo.setCreatedAt(sub.getCreatedAt());
        return vo;
    }

    // ==================== CRUD ====================

    @Override
    public void create(SubscriptionDTO dto) {
        // 检查同用户下名称是否重复
        LambdaQueryWrapper<Subscription> wrapper = new LambdaQueryWrapper<>();
        wrapper.eq(Subscription::getUserId, UserContext.getUserId())
                .eq(Subscription::getName, dto.getName());
        if (count(wrapper) > 0) {
            throw new BusinessException(ErrorCode.SUBSCRIPTION_NAME_EXISTS);
        }

        Subscription sub = new Subscription();
        sub.setUserId(UserContext.getUserId());
        sub.setName(dto.getName());
        sub.setKeywords(toJson(dto.getKeywords()));
        sub.setSourcePlatforms(toJson(dto.getSourcePlatforms()));
        sub.setMatchMode(dto.getMatchMode());
        sub.setCronExpression(dto.getCronExpression());
        sub.setPriority(dto.getPriority());
        sub.setStatus(1);
        save(sub);
    }

    @Override
    public void update(Long id, SubscriptionDTO dto) {
        Subscription existing = super.getById(id);
        if (existing == null || !existing.getUserId().equals(UserContext.getUserId())) {
            throw new BusinessException(ErrorCode.SUBSCRIPTION_NOT_FOUND);
        }

        // 检查名称重复（排除自己）
        LambdaQueryWrapper<Subscription> wrapper = new LambdaQueryWrapper<>();
        wrapper.eq(Subscription::getUserId, UserContext.getUserId())
                .eq(Subscription::getName, dto.getName())
                .ne(Subscription::getId, id);
        if (count(wrapper) > 0) {
            throw new BusinessException(ErrorCode.SUBSCRIPTION_NAME_EXISTS);
        }

        Subscription update = new Subscription();
        update.setId(id);
        update.setName(dto.getName());
        update.setKeywords(toJson(dto.getKeywords()));
        update.setSourcePlatforms(toJson(dto.getSourcePlatforms()));
        update.setMatchMode(dto.getMatchMode());
        update.setCronExpression(dto.getCronExpression());
        update.setPriority(dto.getPriority());
        updateById(update);
    }

    @Override
    public void delete(Long id) {
        Subscription existing =super.getById(id);
        if (existing == null || !existing.getUserId().equals(UserContext.getUserId())) {
            throw new BusinessException(ErrorCode.SUBSCRIPTION_NOT_FOUND);
        }
        removeById(id);
    }

    @Override
    public SubscriptionVO getById(Long id) {
        Subscription sub = super.getById(id);
        if (sub == null || !sub.getUserId().equals(UserContext.getUserId())) {
            throw new BusinessException(ErrorCode.SUBSCRIPTION_NOT_FOUND);
        }
        return convertToVO(sub);
    }

    @Override
    public IPage<SubscriptionVO> list(SubscriptionQueryDTO query) {
        LambdaQueryWrapper<Subscription> wrapper = new LambdaQueryWrapper<>();
        wrapper.eq(Subscription::getUserId, UserContext.getUserId());

        if (StringUtils.hasText(query.getName())) {
            wrapper.like(Subscription::getName, query.getName());
        }
        if (query.getStatus() != null) {
            wrapper.eq(Subscription::getStatus, query.getStatus());
        }
        wrapper.orderByDesc(Subscription::getCreatedAt);

        Page<Subscription> page = new Page<>(query.getCurrent(), query.getSize());
        page(page, wrapper);

        List<SubscriptionVO> records = page.getRecords().stream()
                .map(this::convertToVO)
                .collect(Collectors.toList());

        Page<SubscriptionVO> resultPage = new Page<>(page.getCurrent(), page.getSize(), page.getTotal());
        resultPage.setRecords(records);
        return resultPage;
    }

    // ==================== 核心：手动触发采集 ====================

    @Override
    public void trigger(Long id) {
        // 1. 查询并校验权限
        Subscription sub = super.getById(id);
        if (sub == null || !sub.getUserId().equals(UserContext.getUserId())) {
            throw new BusinessException(ErrorCode.SUBSCRIPTION_NOT_FOUND);
        }
        if (sub.getStatus() == null || sub.getStatus() != 1) {
            throw new BusinessException(ErrorCode.PARAM_ERROR, "订阅规则已暂停");
        }

        // 2. 生成任务ID
        String taskId = UUID.randomUUID().toString().replace("-", "");

        // 3. 尝试获取 Redis 分布式锁（SET NX EX）
        String lockKey = LOCK_PREFIX + id;
        Boolean locked = stringRedisTemplate.opsForValue()
                .setIfAbsent(lockKey, taskId, LOCK_TIMEOUT, TimeUnit.SECONDS);

        if (Boolean.FALSE.equals(locked)) {
            throw new BusinessException(ErrorCode.PARAM_ERROR, "该规则正在执行中，请勿重复触发");
        }

        try {
            // 4. 构造消息体
            TaskTriggerMessage msg = new TaskTriggerMessage();
            msg.setTaskId(taskId);
            msg.setSubscriptionId(id);
            msg.setTriggerTime(LocalDateTime.now().toString());

            // 5. 同步发送 RocketMQ 消息
            SendResult sendResult = rocketMQTemplate.syncSend("nexus-task-trigger", msg);
            if (sendResult == null || !sendResult.getSendStatus().equals(SendStatus.SEND_OK)) {
                throw new BusinessException(ErrorCode.SYSTEM_ERROR, "消息发送失败");
            }

            // 6. 更新最后执行时间
            Subscription update = new Subscription();
            update.setId(id);
            update.setLastRunAt(LocalDateTime.now());
            updateById(update);

        } catch (Exception e) {
            // 发送失败时立即释放锁，允许用户重试
            stringRedisTemplate.delete(lockKey);
            throw e;
        }
        // 发送成功时锁不释放，等 TTL 自动过期（防止 5 分钟内重复触发）
    }
}