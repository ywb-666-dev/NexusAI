package org.ibo.nexusjava.modules.approval.service.impl;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.core.metadata.IPage;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.baomidou.mybatisplus.extension.service.impl.ServiceImpl;
import org.ibo.nexusjava.common.BusinessException;
import org.ibo.nexusjava.common.ErrorCode;
import org.ibo.nexusjava.modules.approval.dto.ApprovalTicketDTO;
import org.ibo.nexusjava.modules.approval.entity.ApprovalTicket;
import org.ibo.nexusjava.modules.approval.mapper.ApprovalTicketMapper;
import org.ibo.nexusjava.modules.approval.service.ApprovalTicketService;
import org.ibo.nexusjava.modules.approval.vo.ApprovalTicketVO;
import org.springframework.stereotype.Service;

import java.time.LocalDateTime;
import java.util.List;
import java.util.stream.Collectors;

@Service
public class ApprovalTicketServiceImpl extends ServiceImpl<ApprovalTicketMapper, ApprovalTicket> implements ApprovalTicketService {

    private ApprovalTicketVO convertToVO(ApprovalTicket ticket) {
        ApprovalTicketVO vo = new ApprovalTicketVO();
        vo.setId(ticket.getId());
        vo.setTaskId(ticket.getTaskId());
        vo.setUserId(ticket.getUserId());
        vo.setActionType(ticket.getActionType());
        vo.setRiskLevel(ticket.getRiskLevel());
        vo.setContext(ticket.getContext());
        vo.setStatus(ticket.getStatus());
        vo.setApprovedBy(ticket.getApprovedBy());
        vo.setApprovedAt(ticket.getApprovedAt());
        vo.setComment(ticket.getComment());
        vo.setCreatedAt(ticket.getCreatedAt());
        return vo;
    }

    @Override
    public IPage<ApprovalTicketVO> listPending(Long current, Long size) {
        LambdaQueryWrapper<ApprovalTicket> wrapper = new LambdaQueryWrapper<>();
        wrapper.eq(ApprovalTicket::getStatus, 0);
        wrapper.orderByDesc(ApprovalTicket::getCreatedAt);

        Page<ApprovalTicket> page = new Page<>(current != null ? current : 1, size != null ? size : 10);
        page(page, wrapper);

        List<ApprovalTicketVO> records = page.getRecords().stream()
                .map(this::convertToVO)
                .collect(Collectors.toList());

        Page<ApprovalTicketVO> resultPage = new Page<>(page.getCurrent(), page.getSize(), page.getTotal());
        resultPage.setRecords(records);
        return resultPage;
    }

    @Override
    public ApprovalTicketVO getById(Long id) {
        ApprovalTicket ticket = super.getById(id);
        if (ticket == null) {
            throw new BusinessException(ErrorCode.APPROVAL_TICKET_NOT_FOUND);
        }
        return convertToVO(ticket);
    }

    @Override
    public void approve(Long id, ApprovalTicketDTO dto) {
        ApprovalTicket ticket = super.getById(id);
        if (ticket == null) {
            throw new BusinessException(ErrorCode.APPROVAL_TICKET_NOT_FOUND);
        }
        if (ticket.getStatus() != 0) {
            throw new BusinessException(ErrorCode.APPROVAL_ALREADY_PROCESSED);
        }
        ticket.setStatus(1);
        ticket.setApprovedBy(dto.getApprovedBy());
        ticket.setComment(dto.getComment());
        ticket.setApprovedAt(LocalDateTime.now());
        updateById(ticket);
    }

    @Override
    public void reject(Long id, ApprovalTicketDTO dto) {
        ApprovalTicket ticket = super.getById(id);
        if (ticket == null) {
            throw new BusinessException(ErrorCode.APPROVAL_TICKET_NOT_FOUND);
        }
        if (ticket.getStatus() != 0) {
            throw new BusinessException(ErrorCode.APPROVAL_ALREADY_PROCESSED);
        }
        ticket.setStatus(2);
        ticket.setApprovedBy(dto.getApprovedBy());
        ticket.setComment(dto.getComment());
        ticket.setApprovedAt(LocalDateTime.now());
        updateById(ticket);
    }
}
