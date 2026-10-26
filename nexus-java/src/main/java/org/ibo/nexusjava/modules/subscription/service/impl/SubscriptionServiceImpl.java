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
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.stereotype.Service;
import org.springframework.util.StringUtils;

import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.time.Duration;
import java.time.LocalDateTime;
import java.util.Collections;
import java.util.List;
import java.util.Set;
import java.util.UUID;
import java.util.concurrent.TimeUnit;
import java.util.stream.Collectors;

@Slf4j
@Service
public class SubscriptionServiceImpl extends ServiceImpl<SubscriptionMapper, Subscription> implements SubscriptionService {

    private final ObjectMapper objectMapper=new ObjectMapper();
    @Autowired private org.ibo.nexusjava.common.JwtUtil jwtUtil;

    @Autowired(required = false)
    private RocketMQTemplate rocketMQTemplate;

    @Autowired
    private StringRedisTemplate stringRedisTemplate;

    private static final HttpClient httpClient = HttpClient.newBuilder()
            .connectTimeout(Duration.ofSeconds(5))
            .version(HttpClient.Version.HTTP_1_1)
            .build();

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
        try { vo.setRssFeeds(objectMapper.readValue(sub.getRssFeeds() == null ? "[]" : sub.getRssFeeds(), new TypeReference<>() {})); }
        catch (Exception e) { vo.setRssFeeds(Collections.emptyList()); }
        vo.setMatchMode(sub.getMatchMode());
        vo.setTriggerConditions(sub.getTriggerConditions());
        vo.setPriority(sub.getPriority());
        vo.setStatus(sub.getStatus());
        vo.setCronExpression(sub.getCronExpression());
        vo.setLastRunAt(sub.getLastRunAt());
        vo.setCreatedAt(sub.getCreatedAt());
        return vo;
    }

    private String validateConditions(String value) {
        if (value == null || value.isBlank()) return "{\"interval_minutes\":60,\"enable_ai\":false}";
        try {
            var node = objectMapper.readTree(value);
            if (!node.isObject()) throw new IllegalArgumentException();
            if (node.has("interval_minutes") && (!node.get("interval_minutes").isIntegralNumber()
                    || node.get("interval_minutes").asInt() < 15 || node.get("interval_minutes").asInt() > 10080))
                throw new IllegalArgumentException();
            if (node.has("enable_ai") && !node.get("enable_ai").isBoolean()) throw new IllegalArgumentException();
            if (node.has("source_policy")) {
                var policy=node.get("source_policy");
                if (!policy.isObject() || !Set.of("auto","manual").contains(policy.path("mode").asText())) throw new IllegalArgumentException();
                if ("auto".equals(policy.path("mode").asText()) && (!policy.path("topic").isTextual() || policy.path("topic").asText().isBlank() || policy.path("topic").asText().length()>200)) throw new IllegalArgumentException();
                if (policy.has("language") && !Set.of("zh_first","all").contains(policy.path("language").asText())) throw new IllegalArgumentException();
                if (policy.has("excluded_ids")) {
                    var ids=policy.get("excluded_ids");
                    if (!ids.isArray() || ids.size()>50) throw new IllegalArgumentException();
                    for (var id:ids) if (!id.isTextual() || !id.asText().matches("[0-9a-f]{16}")) throw new IllegalArgumentException();
                }
            }
            return objectMapper.writeValueAsString(node);
        } catch (Exception e) { throw new BusinessException(ErrorCode.PARAM_ERROR, "请检查采集间隔（15至10080分钟）、AI开关及自动来源策略（主题、语言和排除列表）"); }
    }

    private List<SubscriptionDTO.RssFeedItem> prepareSources(SubscriptionDTO dto) {
        try {
            var conditions = objectMapper.readTree(validateConditions(dto.getTriggerConditions()));
            var policy = conditions.path("source_policy");
            boolean automatic = "auto".equals(policy.path("mode").asText());
            var feeds = new java.util.ArrayList<SubscriptionDTO.RssFeedItem>();
            var seen = new java.util.HashSet<String>();
            var preserved = new java.util.ArrayList<SubscriptionDTO.RssFeedItem>();
            for (var feed : dto.getRssFeeds() == null ? List.<SubscriptionDTO.RssFeedItem>of() : dto.getRssFeeds()) {
                if (automatic && "system".equals(feed.getOrigin())) { preserved.add(feed); continue; }
                if (seen.add(feed.getUrl())) { feed.setOrigin("manual"); feed.setSourceId(null); feed.setReason(null); feeds.add(feed); }
            }
            // Pausing an existing configuration must not depend on the collection service.
            if (automatic && Integer.valueOf(0).equals(dto.getStatus()) && !preserved.isEmpty()) {
                var excluded = new java.util.HashSet<String>();
                for (var id : policy.path("excluded_ids")) excluded.add(id.asText());
                for (var feed : preserved) if (!excluded.contains(feed.getSourceId()) && seen.add(feed.getUrl())) feeds.add(feed);
                return feeds;
            }
            if (automatic && feeds.size() < 20) {
                var body = policy.deepCopy();
                ((com.fasterxml.jackson.databind.node.ObjectNode)body).put("limit", Math.min(5,20-feeds.size()));
                var request = HttpRequest.newBuilder(URI.create("http://localhost:8000/api/python/subscriptions/resolve-sources"))
                    .header("Authorization", "Bearer " + jwtUtil.generateToken(UserContext.getUserId(),UserContext.getUsername(),UserContext.getRole()))
                    .header("Content-Type", "application/json").timeout(Duration.ofSeconds(35))
                    .POST(HttpRequest.BodyPublishers.ofString(objectMapper.writeValueAsString(body))).build();
                var response = httpClient.send(request,HttpResponse.BodyHandlers.ofString());
                var result = objectMapper.readTree(response.body());
                if (response.statusCode()!=200 || result.path("code").asInt()!=200)
                    throw new BusinessException(ErrorCode.PARAM_ERROR,result.path("message").asText("自动匹配来源失败，请稍后重试"));
                for (var node : result.path("data").path("feeds")) {
                    var feed = objectMapper.treeToValue(node,SubscriptionDTO.RssFeedItem.class);
                    if (seen.add(feed.getUrl())) feeds.add(feed);
                }
                if (feeds.isEmpty()) throw new BusinessException(ErrorCode.PARAM_ERROR,result.path("data").path("notice").asText("未找到可用来源"));
            }
            if (feeds.isEmpty()) throw new BusinessException(ErrorCode.PARAM_ERROR,"请添加采集源，或开启自动匹配并填写关注主题");
            if (feeds.size()>20) throw new BusinessException(ErrorCode.PARAM_ERROR,"每个订阅最多20个来源");
            return feeds;
        } catch (BusinessException e) { throw e; }
        catch (Exception e) { log.warn("Automatic source resolution failed: {}",e.toString()); throw new BusinessException(ErrorCode.SYSTEM_ERROR,"来源匹配服务暂不可用，请稍后重试"); }
    }

    // ==================== CRUD ====================

    @Override
    public void create(SubscriptionDTO dto) {
        // 检查同用户下名称是否重复
        LambdaQueryWrapper<Subscription> wrapper = new LambdaQueryWrapper<>();
        wrapper.eq(Subscription::getUserId, UserContext.getUserId())
                .eq(Subscription::getName, dto.getName()).ne(Subscription::getStatus, -1);
        if (count(wrapper) > 0) {
            throw new BusinessException(ErrorCode.SUBSCRIPTION_NAME_EXISTS);
        }

        var feeds = prepareSources(dto);
        Subscription sub = new Subscription();
        sub.setUserId(UserContext.getUserId());
        sub.setName(dto.getName());
        sub.setKeywords(toJson(dto.getKeywords()));
        sub.setSourcePlatforms(toJson(feeds.stream().map(SubscriptionDTO.RssFeedItem::getPlatform).distinct().toList()));
        try { sub.setRssFeeds(objectMapper.writeValueAsString(feeds)); }
        catch (Exception e) { throw new BusinessException(ErrorCode.PARAM_ERROR, "RSS source serialization failed"); }
        sub.setMatchMode(dto.getMatchMode());
        sub.setCronExpression(dto.getCronExpression());
        sub.setPriority(dto.getPriority());
        sub.setStatus(dto.getStatus() == null ? 1 : dto.getStatus());
        sub.setTriggerConditions(validateConditions(dto.getTriggerConditions()));
        save(sub);
    }

    @Override
    public void update(Long id, SubscriptionDTO dto) {
        Subscription existing = super.getById(id);
        if (existing == null || !existing.getUserId().equals(UserContext.getUserId()) || existing.getStatus() == -1) {
            throw new BusinessException(ErrorCode.SUBSCRIPTION_NOT_FOUND);
        }

        // 检查名称重复（排除自己）
        LambdaQueryWrapper<Subscription> wrapper = new LambdaQueryWrapper<>();
        wrapper.eq(Subscription::getUserId, UserContext.getUserId())
                .eq(Subscription::getName, dto.getName()).ne(Subscription::getStatus, -1)
                .ne(Subscription::getId, id);
        if (count(wrapper) > 0) {
            throw new BusinessException(ErrorCode.SUBSCRIPTION_NAME_EXISTS);
        }

        var feeds = prepareSources(dto);
        Subscription update = new Subscription();
        update.setId(id);
        update.setName(dto.getName());
        update.setKeywords(toJson(dto.getKeywords()));
        update.setSourcePlatforms(toJson(feeds.stream().map(SubscriptionDTO.RssFeedItem::getPlatform).distinct().toList()));
        try { update.setRssFeeds(objectMapper.writeValueAsString(feeds)); }
        catch (Exception e) { throw new BusinessException(ErrorCode.PARAM_ERROR, "RSS source serialization failed"); }
        update.setMatchMode(dto.getMatchMode());
        update.setCronExpression(dto.getCronExpression());
        update.setPriority(dto.getPriority());
        update.setStatus(dto.getStatus());
        update.setTriggerConditions(validateConditions(dto.getTriggerConditions()));
        updateById(update);
    }

    @Override
    public void delete(Long id) {
        Subscription existing =super.getById(id);
        if (existing == null || !existing.getUserId().equals(UserContext.getUserId()) || existing.getStatus() == -1) {
            throw new BusinessException(ErrorCode.SUBSCRIPTION_NOT_FOUND);
        }
        existing.setStatus(-1);
        updateById(existing);
    }

    @Override
    public SubscriptionVO getById(Long id) {
        Subscription sub = super.getById(id);
        if (sub == null || !sub.getUserId().equals(UserContext.getUserId()) || sub.getStatus() == -1) {
            throw new BusinessException(ErrorCode.SUBSCRIPTION_NOT_FOUND);
        }
        return convertToVO(sub);
    }

    @Override
    public IPage<SubscriptionVO> list(SubscriptionQueryDTO query) {
        LambdaQueryWrapper<Subscription> wrapper = new LambdaQueryWrapper<>();
        wrapper.eq(Subscription::getUserId, UserContext.getUserId()).ne(Subscription::getStatus, -1);

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
    public String trigger(Long id) {
        Subscription sub = super.getById(id);
        if (sub == null || !sub.getUserId().equals(UserContext.getUserId()) || sub.getStatus() == -1)
            throw new BusinessException(ErrorCode.SUBSCRIPTION_NOT_FOUND);
        if (sub.getStatus() != 1) throw new BusinessException(ErrorCode.PARAM_ERROR, "订阅已暂停");
        try {
            var request = HttpRequest.newBuilder(URI.create("http://localhost:8000/api/python/agent/tasks?subscription_id=" + id))
                .header("Authorization", "Bearer " + jwtUtil.generateToken(UserContext.getUserId(), UserContext.getUsername(), UserContext.getRole()))
                .timeout(Duration.ofSeconds(15)).POST(HttpRequest.BodyPublishers.noBody()).build();
            var response = httpClient.send(request, HttpResponse.BodyHandlers.ofString());
            var result = objectMapper.readTree(response.body());
            if (response.statusCode() != 200 || result.path("code").asInt() != 200)
                throw new BusinessException(ErrorCode.SYSTEM_ERROR, result.path("message").asText("采集任务创建失败"));
            return result.path("data").path("task_id").asText();
        } catch (BusinessException e) { throw e; }
        catch (Exception e) { throw new BusinessException(ErrorCode.SYSTEM_ERROR, "采集服务不可用，请稍后重试"); }
    }
}
