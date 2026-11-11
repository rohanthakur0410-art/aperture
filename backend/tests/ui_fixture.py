"""Isolated UI fixtures. Never used by the production app or described as live AI."""
import copy
from app import main, llm, rag
main.KEY='ui-fixture-not-a-credential'
questions=[
 ('Evaluating a classifier','Your resume mentions a customer-churn classifier. Suppose it performs well on training data but poorly on new customers. How would you tell whether the problem is overfitting, and how would you redesign your evaluation?','Connects your classification project to the textbook discussion of generalization and independent evaluation.'),
 ('Decision tree trade-offs','You used decision trees in your project. How would you decide whether pruning the tree improves generalization, without repeatedly checking the final test set?','Follows your evaluation answer into a practical model-selection trade-off.'),
 ('Learning from limited data','If the available churn dataset became much smaller, how would you compare two models while keeping your estimate of performance honest?','Builds on your Python and machine-learning background and the distinction between model selection and final evaluation.'),
 ('Explaining the result','A teammate says that a model with 95% training accuracy is ready to deploy. What additional evidence would you ask for, and how would you explain your concern?','Tests whether you can apply generalization concepts to a real team decision.')]
async def fixture_generate(payload,schema):
 if schema==llm.QUESTION_SCHEMA:
  i=len(payload['previous']);topic,q,why=questions[i]
  return {'question':q,'topic':topic,'rationale':why,'source_ids':[payload['sources'][0]['id']],'expected_points':['Use unseen evaluation data','Keep final test data separate from model selection']}
 return {'overview':'You explained why training performance is not enough and connected model choices to an independent evaluation. Your answers were clearest when you named a specific check. The next step is to make the evaluation plan more precise.','strengths':['You separated model training from evaluation on unseen examples.','You explained pruning as a trade-off rather than a guaranteed improvement.'],'practice_next':['Practise choosing an evaluation metric when the classes are imbalanced.','Explain how you would use validation folds without leaking information into the final test.'],'observations':[{'question_number':1,'assessment':'You identified the gap between training accuracy and generalization, then proposed a separate test set.','evidence':'I would compare training and validation performance.'},{'question_number':2,'assessment':'You tied pruning to validation performance instead of assuming a smaller tree is always better.','evidence':'I would tune pruning with cross-validation.'},{'question_number':3,'assessment':'You suggested using folds to make better use of a small dataset. More detail on leakage would make this stronger.','evidence':'I would use stratified cross-validation.'},{'question_number':4,'assessment':'You asked for independent evidence before accepting a deployment claim.','evidence':'I would ask for performance on unseen data.'}]}
llm.generate=fixture_generate
app=main.app
