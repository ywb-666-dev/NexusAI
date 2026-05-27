package org.ibo.nexusjava.modules.subscription.controller;

import com.baomidou.mybatisplus.core.metadata.IPage;
import jakarta.validation.Valid;
import org.ibo.nexusjava.common.Result;
import org.ibo.nexusjava.modules.subscription.dto.SubscriptionDTO;
import org.ibo.nexusjava.modules.subscription.dto.SubscriptionQueryDTO;
import org.ibo.nexusjava.modules.subscription.service.SubscriptionService;
import org.ibo.nexusjava.modules.subscription.vo.SubscriptionVO;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/java/subscriptions")
public class SubscriptionController {

    @Autowired
    private SubscriptionService subscriptionService;

    @PostMapping
    public Result<Void> create(@Valid @RequestBody SubscriptionDTO dto) {
        subscriptionService.create(dto);
        return Result.success();
    }

    @PutMapping("/{id}")
    public Result<Void> update(@PathVariable Long id, @Valid @RequestBody SubscriptionDTO dto) {
        subscriptionService.update(id, dto);
        return Result.success();
    }

    @DeleteMapping("/{id}")
    public Result<Void> delete(@PathVariable Long id) {
        subscriptionService.delete(id);
        return Result.success();
    }

    @GetMapping("/{id}")
    public Result<SubscriptionVO> getById(@PathVariable Long id) {
        return Result.success(subscriptionService.getById(id));
    }

    @GetMapping
    public Result<IPage<SubscriptionVO>> list(SubscriptionQueryDTO query) {
        return Result.success(subscriptionService.list(query));
    }

    @PostMapping("/{id}/trigger")
    public Result<Void> trigger(@PathVariable Long id) {
        subscriptionService.trigger(id);
        return Result.success();
    }
}