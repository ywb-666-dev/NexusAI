package org.ibo.nexusjava.modules.audit.service.impl;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.core.metadata.IPage;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.baomidou.mybatisplus.extension.service.impl.ServiceImpl;
import org.ibo.nexusjava.modules.audit.entity.AuditLog;
import org.ibo.nexusjava.modules.audit.mapper.AuditLogMapper;
import org.ibo.nexusjava.modules.audit.service.AuditLogService;
import org.ibo.nexusjava.modules.audit.vo.AuditLogVO;
import org.springframework.stereotype.Service;

import java.util.List;
import java.util.stream.Collectors;

@Service
public class AuditLogServiceImpl extends ServiceImpl<AuditLogMapper, AuditLog> implements AuditLogService {

    private AuditLogVO convertToVO(AuditLog log) {
        AuditLogVO vo = new AuditLogVO();
        vo.setId(log.getId());
        vo.setUserId(log.getUserId());
        vo.setAction(log.getAction());
        vo.setTargetType(log.getTargetType());
        vo.setTargetId(log.getTargetId());
        vo.setActionTime(log.getActionTime());
        vo.setIpAddress(log.getIpAddress());
        vo.setRequestId(log.getRequestId());
        return vo;
    }

    @Override
    public IPage<AuditLogVO> list(Long current, Long size) {
        LambdaQueryWrapper<AuditLog> wrapper = new LambdaQueryWrapper<>();
        wrapper.orderByDesc(AuditLog::getActionTime);

        Page<AuditLog> page = new Page<>(current != null ? current : 1, size != null ? size : 10);
        page(page, wrapper);

        List<AuditLogVO> records = page.getRecords().stream()
                .map(this::convertToVO)
                .collect(Collectors.toList());

        Page<AuditLogVO> resultPage = new Page<>(page.getCurrent(), page.getSize(), page.getTotal());
        resultPage.setRecords(records);
        return resultPage;
    }
}
