package org.ibo.nexusjava.modules.content.service.impl;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.core.metadata.IPage;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.baomidou.mybatisplus.extension.service.impl.ServiceImpl;
import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.ibo.nexusjava.common.BusinessException;
import org.ibo.nexusjava.common.ErrorCode;
import org.ibo.nexusjava.modules.content.entity.Content;
import org.ibo.nexusjava.modules.content.mapper.ContentMapper;
import org.ibo.nexusjava.modules.content.service.ContentService;
import org.ibo.nexusjava.modules.content.vo.ContentVO;
import org.ibo.nexusjava.modules.subscription.entity.Subscription;
import org.ibo.nexusjava.modules.subscription.mapper.SubscriptionMapper;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import org.springframework.util.StringUtils;

import java.util.Collections;
import java.util.List;
import java.util.UUID;
import java.util.stream.Collectors;

@Service
public class ContentServiceImpl extends ServiceImpl<ContentMapper, Content> implements ContentService {

    private final ObjectMapper objectMapper = new ObjectMapper();

    @Autowired
    private SubscriptionMapper subscriptionMapper;

    private ContentVO convertToVO(Content content) {
        ContentVO vo = new ContentVO();
        vo.setId(content.getId());
        vo.setSubscriptionId(content.getSubscriptionId());
        vo.setSourcePlatform(content.getSourcePlatform());
        vo.setSourceUrl(content.getSourceUrl());
        vo.setTitle(content.getTitle());
        vo.setSummary(content.getSummary());
        vo.setAuthor(content.getAuthor());
        vo.setPublishedAt(content.getPublishedAt());
        vo.setFetchedAt(content.getFetchedAt());
        vo.setIsDuplicate(content.getIsDuplicate());
        vo.setDuplicateOf(content.getDuplicateOf());
        vo.setCreatedAt(content.getCreatedAt());

        // 关联查询订阅名称
        Subscription sub = subscriptionMapper.selectById(content.getSubscriptionId());
        vo.setSubscriptionName(sub != null ? sub.getName() : "未知");

        // relatedContents JSON 反序列化
        if (StringUtils.hasText(content.getRelatedContents())) {
            try {
                List<String> related = objectMapper.readValue(content.getRelatedContents(), new TypeReference<List<String>>() {});
                vo.setRelatedContents(related);
            } catch (Exception e) {
                vo.setRelatedContents(Collections.emptyList());
            }
        } else {
            vo.setRelatedContents(Collections.emptyList());
        }

        return vo;
    }

    @Override
    public IPage<ContentVO> listBySubscription(Long subscriptionId, Long current, Long size) {
        LambdaQueryWrapper<Content> wrapper = new LambdaQueryWrapper<>();
        wrapper.eq(Content::getStatus, 1); // 只查有效内容

        if (subscriptionId != null) {
            wrapper.eq(Content::getSubscriptionId, subscriptionId);
        }

        wrapper.orderByDesc(Content::getFetchedAt);

        Page<Content> page = new Page<>(current != null ? current : 1, size != null ? size : 10);
        page(page, wrapper);

        List<ContentVO> records = page.getRecords().stream()
                .map(this::convertToVO)
                .collect(Collectors.toList());

        Page<ContentVO> resultPage = new Page<>(page.getCurrent(), page.getSize(), page.getTotal());
        resultPage.setRecords(records);
        return resultPage;
    }

    @Override
    public ContentVO getById(String id) {
        Content content = super.getById(UUID.fromString(id));
        if (content == null || content.getStatus() == null || content.getStatus() != 1) {
            throw new BusinessException(ErrorCode.PARAM_ERROR, "内容不存在");
        }
        return convertToVO(content);
    }
}