ALTER TABLE farms."alert_events"
  ADD CONSTRAINT "alert_events_causation_id_fkey"
  FOREIGN KEY ("causation_id") REFERENCES farms."alert_events" ("id")
  ON DELETE SET NULL ON UPDATE NO ACTION NOT DEFERRABLE;

ALTER TABLE farms."cadastros_areas_rurais"
  ADD CONSTRAINT "cadastros_areas_rurais_parent_id_fkey"
  FOREIGN KEY ("parent_id") REFERENCES farms."cadastros_areas_rurais" ("id")
  ON DELETE SET NULL ON UPDATE NO ACTION NOT DEFERRABLE;

ALTER TABLE farms."cadastros_categorias_produto"
  ADD CONSTRAINT "cadastros_categorias_produto_parent_id_fkey"
  FOREIGN KEY ("parent_id") REFERENCES farms."cadastros_categorias_produto" ("id")
  ON DELETE SET NULL ON UPDATE NO ACTION NOT DEFERRABLE;

ALTER TABLE farms."cadastros_produtos"
  ADD CONSTRAINT "cadastros_produtos_produto_referencia_id_fkey"
  FOREIGN KEY ("produto_referencia_id") REFERENCES farms."cadastros_produtos" ("id")
  ON DELETE SET NULL ON UPDATE NO ACTION NOT DEFERRABLE;

ALTER TABLE farms."caderno_campo_entradas"
  ADD CONSTRAINT "caderno_campo_entradas_retifica_evento_id_fkey"
  FOREIGN KEY ("retifica_evento_id") REFERENCES farms."caderno_campo_entradas" ("id")
  ON DELETE SET NULL ON UPDATE NO ACTION NOT DEFERRABLE;

ALTER TABLE farms."caderno_campo_entradas"
  ADD CONSTRAINT "caderno_campo_entradas_retificado_por_evento_id_fkey"
  FOREIGN KEY ("retificado_por_evento_id") REFERENCES farms."caderno_campo_entradas" ("id")
  ON DELETE SET NULL ON UPDATE NO ACTION NOT DEFERRABLE;

ALTER TABLE farms."categoria_custom"
  ADD CONSTRAINT "categoria_custom_parent_id_fkey"
  FOREIGN KEY ("parent_id") REFERENCES farms."categoria_custom" ("id")
  ON DELETE SET NULL ON UPDATE NO ACTION NOT DEFERRABLE;

ALTER TABLE farms."estoque_movimentos"
  ADD CONSTRAINT "estoque_movimentos_ajuste_de_fkey"
  FOREIGN KEY ("ajuste_de") REFERENCES farms."estoque_movimentos" ("id")
  ON DELETE SET NULL ON UPDATE NO ACTION NOT DEFERRABLE;

ALTER TABLE farms."fin_planos_conta"
  ADD CONSTRAINT "fin_planos_conta_parent_id_fkey"
  FOREIGN KEY ("parent_id") REFERENCES farms."fin_planos_conta" ("id")
  ON DELETE RESTRICT ON UPDATE NO ACTION NOT DEFERRABLE;

ALTER TABLE farms."imoveis_documentos"
  ADD CONSTRAINT "imoveis_documentos_substituido_por_fkey"
  FOREIGN KEY ("substituido_por") REFERENCES farms."imoveis_documentos" ("id")
  ON DELETE SET NULL ON UPDATE NO ACTION NOT DEFERRABLE;

ALTER TABLE farms."pec_animais"
  ADD CONSTRAINT "pec_animais_mae_id_fkey"
  FOREIGN KEY ("mae_id") REFERENCES farms."pec_animais" ("id")
  ON DELETE SET NULL ON UPDATE NO ACTION NOT DEFERRABLE;

ALTER TABLE farms."pec_animais"
  ADD CONSTRAINT "pec_animais_pai_id_fkey"
  FOREIGN KEY ("pai_id") REFERENCES farms."pec_animais" ("id")
  ON DELETE SET NULL ON UPDATE NO ACTION NOT DEFERRABLE;

ALTER TABLE farms."planos_operacionais_tarefas_insumos"
  ADD CONSTRAINT "planos_operacionais_tarefas_insumos_substitui_item_id_fkey"
  FOREIGN KEY ("substitui_item_id") REFERENCES farms."planos_operacionais_tarefas_insumos" ("id")
  ON DELETE SET NULL ON UPDATE NO ACTION NOT DEFERRABLE;

ALTER TABLE farms."recommendation_results"
  ADD CONSTRAINT "recommendation_results_superseded_by_id_fkey"
  FOREIGN KEY ("superseded_by_id") REFERENCES farms."recommendation_results" ("id")
  ON DELETE SET NULL ON UPDATE NO ACTION NOT DEFERRABLE;

ALTER TABLE farms."production_units"
  ADD CONSTRAINT "production_units_cultivo_area_id_fkey"
  FOREIGN KEY ("cultivo_area_id") REFERENCES farms."cultivo_areas" ("id")
  ON DELETE SET NULL ON UPDATE NO ACTION NOT DEFERRABLE;

ALTER TABLE farms."romaneios_colheita"
  ADD CONSTRAINT "romaneios_colheita_qualidade_laudo_id_fkey"
  FOREIGN KEY ("qualidade_laudo_id") REFERENCES farms."operacional_qualidade_laudos" ("id")
  ON DELETE SET NULL ON UPDATE NO ACTION NOT DEFERRABLE;

ALTER TABLE farms."operacoes_agricolas"
  ADD CONSTRAINT "operacoes_agricolas_tarefa_id_fkey"
  FOREIGN KEY ("tarefa_id") REFERENCES farms."safra_tarefas" ("id")
  ON DELETE SET NULL ON UPDATE NO ACTION NOT DEFERRABLE;
